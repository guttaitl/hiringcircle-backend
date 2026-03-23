from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
from pydantic import BaseModel
import os
import openai
from datetime import datetime

from api.db import get_db
from api.utils.security import get_current_user

router = APIRouter()

# =========================================================
# OPENAI CLIENT SETUP
# =========================================================

openai.api_key = os.getenv("OPENAI_API_KEY", "")

# =========================================================
# AI MATCH MODELS
# =========================================================

class JobResumeMatchRequest(BaseModel):
    job_id: str
    top_k: Optional[int] = 10

class CandidateMatchRequest(BaseModel):
    resume_id: str
    top_k: Optional[int] = 10

class MatchResult(BaseModel):
    match_id: str
    job_id: Optional[str]
    resume_id: Optional[str]
    match_score: float
    match_reasons: List[str]
    skill_match: dict
    experience_match: dict
    overall_fit: str

# =========================================================
# AI ANALYSIS FUNCTIONS
# =========================================================

async def analyze_job_resume_match(job_text: str, resume_text: str) -> dict:
    """Use OpenAI to analyze match between job and resume"""
    
    if not openai.api_key:
        # Fallback scoring if no API key
        return fallback_match_analysis(job_text, resume_text)
    
    try:
        prompt = f"""
        Analyze the match between this job description and candidate resume.
        
        JOB DESCRIPTION:
        {job_text[:2000]}
        
        CANDIDATE RESUME:
        {resume_text[:2000]}
        
        Provide a JSON response with:
        1. overall_score (0-100): Overall match percentage
        2. skill_match_score (0-100): How well skills match
        3. experience_match_score (0-100): How well experience matches
        4. key_matching_skills: List of skills that match
        5. missing_skills: List of required skills candidate lacks
        6. experience_years_match: Whether experience level matches
        7. overall_fit: One of "Excellent", "Good", "Fair", "Poor"
        8. reasoning: Brief explanation of the match
        
        Format as valid JSON only.
        """
        
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert recruiter AI that analyzes job-candidate matches."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=800
        )
        
        import json
        result_text = response.choices[0].message.content
        
        # Extract JSON from response
        try:
            result = json.loads(result_text)
        except:
            # Try to extract JSON from markdown code block
            import re
            json_match = re.search(r'```json\n(.*?)\n```', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                return fallback_match_analysis(job_text, resume_text)
        
        return {
            "overall_score": result.get("overall_score", 50),
            "skill_match_score": result.get("skill_match_score", 50),
            "experience_match_score": result.get("experience_match_score", 50),
            "key_matching_skills": result.get("key_matching_skills", []),
            "missing_skills": result.get("missing_skills", []),
            "experience_years_match": result.get("experience_years_match", False),
            "overall_fit": result.get("overall_fit", "Fair"),
            "reasoning": result.get("reasoning", "")
        }
        
    except Exception as e:
        print(f"OpenAI analysis error: {e}")
        return fallback_match_analysis(job_text, resume_text)

def fallback_match_analysis(job_text: str, resume_text: str) -> dict:
    """Fallback keyword-based matching when OpenAI is unavailable"""
    
    job_lower = job_text.lower()
    resume_lower = resume_text.lower()
    
    # Common tech skills to check
    common_skills = [
        "python", "javascript", "java", "react", "node", "sql", "aws",
        "docker", "kubernetes", "machine learning", "ai", "data analysis",
        "project management", "agile", "scrum", "leadership", "communication",
        "typescript", "next.js", "vue", "angular", "mongodb", "postgresql",
        "redis", "graphql", "rest api", "git", "ci/cd", "jenkins",
        "tensorflow", "pytorch", "pandas", "numpy", "tableau", "power bi"
    ]
    
    matching_skills = []
    missing_skills = []
    
    for skill in common_skills:
        in_job = skill in job_lower
        in_resume = skill in resume_lower
        
        if in_job and in_resume:
            matching_skills.append(skill)
        elif in_job and not in_resume:
            missing_skills.append(skill)
    
    # Calculate scores
    job_skills_found = sum(1 for s in common_skills if s in job_lower)
    if job_skills_found > 0:
        skill_match_score = (len(matching_skills) / job_skills_found) * 100
    else:
        skill_match_score = 50
    
    # Experience matching (simple keyword check)
    exp_keywords = ["years", "experience", "senior", "junior", "lead", "manager"]
    exp_matches = sum(1 for kw in exp_keywords if kw in job_lower and kw in resume_lower)
    experience_match_score = (exp_matches / len(exp_keywords)) * 100
    
    # Overall score
    overall_score = (skill_match_score * 0.6) + (experience_match_score * 0.4)
    
    # Determine fit
    if overall_score >= 80:
        overall_fit = "Excellent"
    elif overall_score >= 60:
        overall_fit = "Good"
    elif overall_score >= 40:
        overall_fit = "Fair"
    else:
        overall_fit = "Poor"
    
    return {
        "overall_score": round(overall_score, 1),
        "skill_match_score": round(skill_match_score, 1),
        "experience_match_score": round(experience_match_score, 1),
        "key_matching_skills": matching_skills[:10],
        "missing_skills": missing_skills[:10],
        "experience_years_match": experience_match_score > 50,
        "overall_fit": overall_fit,
        "reasoning": f"Matched {len(matching_skills)} skills. Missing {len(missing_skills)} required skills."
    }

# =========================================================
# AI MATCH ROUTES
# =========================================================

@router.post("/ai-match/job-to-candidates")
async def match_job_to_candidates(
    request: JobResumeMatchRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Find best matching candidates for a job"""
    
    # Get job details
    job_result = db.execute(
        text("""
        SELECT 
            jobid,
            job_title,
            job_description,
            skills,
            experience,
            location
        FROM job_postings
        WHERE jobid = :job_id
        """),
        {"job_id": request.job_id}
    )
    
    job = job_result.fetchone()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Build job text for analysis
    job_text = f"""
    Title: {job.job_title}
    Description: {job.job_description or ''}
    Skills Required: {job.skills or ''}
    Experience: {job.experience or ''}
    Location: {job.location or ''}
    """
    
    # Get all active resumes
    resumes_result = db.execute(
        text("""
        SELECT 
            id,
            full_name,
            email,
            skills,
            experience,
            location,
            resume_text
        FROM resumes
        ORDER BY created_at DESC
        LIMIT 100
        """))
    
    resumes = resumes_result.fetchall()
    
    # Analyze matches
    matches = []
    for resume in resumes:
        resume_text = f"""
        Name: {resume.full_name}
        Skills: {resume.skills or ''}
        Experience: {resume.experience or ''}
        Location: {resume.location or ''}
        Resume: {resume.resume_text or ''}
        """
        
        analysis = await analyze_job_resume_match(job_text, resume_text)
        
        match_id = f"{request.job_id}_{resume.id}"
        
        matches.append({
            "match_id": match_id,
            "job_id": request.job_id,
            "resume_id": resume.id,
            "candidate_name": resume.full_name,
            "candidate_email": resume.email,
            "match_score": analysis["overall_score"],
            "skill_match_score": analysis["skill_match_score"],
            "experience_match_score": analysis["experience_match_score"],
            "key_matching_skills": analysis["key_matching_skills"],
            "missing_skills": analysis["missing_skills"],
            "overall_fit": analysis["overall_fit"],
            "reasoning": analysis["reasoning"]
        })
    
    # Sort by match score
    matches.sort(key=lambda x: x["match_score"], reverse=True)
    
    # Return top K matches
    top_matches = matches[:request.top_k]
    
    # Store match results in database
    for match in top_matches:
        db.execute(
            text("""
            INSERT INTO ai_matches (
                match_id,
                job_id,
                resume_id,
                match_score,
                skill_match_score,
                experience_match_score,
                overall_fit,
                reasoning,
                created_at,
                created_by
            ) VALUES (
                :match_id,
                :job_id,
                :resume_id,
                :match_score,
                :skill_match_score,
                :experience_match_score,
                :overall_fit,
                :reasoning,
                NOW(),
                :created_by
            )
            ON CONFLICT (match_id) DO UPDATE SET
                match_score = EXCLUDED.match_score,
                skill_match_score = EXCLUDED.skill_match_score,
                experience_match_score = EXCLUDED.experience_match_score,
                overall_fit = EXCLUDED.overall_fit,
                reasoning = EXCLUDED.reasoning,
                updated_at = NOW()
            """),
            {
                "match_id": match["match_id"],
                "job_id": match["job_id"],
                "resume_id": match["resume_id"],
                "match_score": match["match_score"],
                "skill_match_score": match["skill_match_score"],
                "experience_match_score": match["experience_match_score"],
                "overall_fit": match["overall_fit"],
                "reasoning": match["reasoning"],
                "created_by": current_user.get("email")
            }
        )
    
    db.commit()
    
    return {
        "success": True,
        "job_id": request.job_id,
        "job_title": job.job_title,
        "total_candidates": len(resumes),
        "matches_found": len(top_matches),
        "matches": top_matches
    }

@router.post("/ai-match/candidate-to-jobs")
async def match_candidate_to_jobs(
    request: CandidateMatchRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Find best matching jobs for a candidate"""
    
    # Get resume details
    resume_result = db.execute(
        text("""
        SELECT 
            id,
            full_name,
            skills,
            experience,
            location,
            resume_text
        FROM resumes
        WHERE id = :resume_id
        """),
        {"resume_id": request.resume_id}
    )
    
    resume = resume_result.fetchone()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Build resume text for analysis
    resume_text = f"""
    Name: {resume.full_name}
    Skills: {resume.skills or ''}
    Experience: {resume.experience or ''}
    Location: {resume.location or ''}
    Resume: {resume.resume_text or ''}
    """
    
    # Get all active jobs
    jobs_result = db.execute(
        text("""
        SELECT 
            jobid,
            job_title,
            job_description,
            skills,
            experience,
            location,
            client_name
        FROM job_postings
        ORDER BY created_at DESC
        LIMIT 100
        """))
    
    jobs = jobs_result.fetchall()
    
    # Analyze matches
    matches = []
    for job in jobs:
        job_text = f"""
        Title: {job.job_title}
        Description: {job.job_description or ''}
        Skills Required: {job.skills or ''}
        Experience: {job.experience or ''}
        Location: {job.location or ''}
        """
        
        analysis = await analyze_job_resume_match(job_text, resume_text)
        
        match_id = f"{job.jobid}_{request.resume_id}"
        
        matches.append({
            "match_id": match_id,
            "job_id": job.jobid,
            "job_title": job.job_title,
            "client_name": job.client_name,
            "resume_id": request.resume_id,
            "candidate_name": resume.full_name,
            "match_score": analysis["overall_score"],
            "skill_match_score": analysis["skill_match_score"],
            "experience_match_score": analysis["experience_match_score"],
            "key_matching_skills": analysis["key_matching_skills"],
            "missing_skills": analysis["missing_skills"],
            "overall_fit": analysis["overall_fit"],
            "reasoning": analysis["reasoning"]
        })
    
    # Sort by match score
    matches.sort(key=lambda x: x["match_score"], reverse=True)
    
    # Return top K matches
    top_matches = matches[:request.top_k]
    
    return {
        "success": True,
        "resume_id": request.resume_id,
        "candidate_name": resume.full_name,
        "total_jobs": len(jobs),
        "matches_found": len(top_matches),
        "matches": top_matches
    }

@router.get("/ai-match/history")
def get_match_history(
    job_id: Optional[str] = None,
    resume_id: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get AI match history"""
    
    offset = (page - 1) * limit
    
    query = """
        SELECT 
            m.match_id,
            m.job_id,
            j.job_title,
            m.resume_id,
            r.full_name as candidate_name,
            m.match_score,
            m.skill_match_score,
            m.experience_match_score,
            m.overall_fit,
            m.reasoning,
            m.created_at
        FROM ai_matches m
        LEFT JOIN job_postings j ON m.job_id = j.jobid
        LEFT JOIN resumes r ON m.resume_id = r.id
        WHERE 1=1
    """
    
    params = {"limit": limit, "offset": offset}
    
    if job_id:
        query += " AND m.job_id = :job_id"
        params["job_id"] = job_id
    
    if resume_id:
        query += " AND m.resume_id = :resume_id"
        params["resume_id"] = resume_id
    
    query += " ORDER BY m.created_at DESC LIMIT :limit OFFSET :offset"
    
    result = db.execute(text(query), params)
    rows = result.fetchall()
    
    matches = []
    for row in rows:
        matches.append({
            "match_id": row.match_id,
            "job_id": row.job_id,
            "job_title": row.job_title,
            "resume_id": row.resume_id,
            "candidate_name": row.candidate_name,
            "match_score": row.match_score,
            "skill_match_score": row.skill_match_score,
            "experience_match_score": row.experience_match_score,
            "overall_fit": row.overall_fit,
            "reasoning": row.reasoning,
            "created_at": row.created_at
        })
    
    return {
        "success": True,
        "page": page,
        "limit": limit,
        "matches": matches
    }

@router.get("/ai-match/stats")
def get_match_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get AI matching statistics"""
    
    # Total matches
    total_result = db.execute(text("SELECT COUNT(*) FROM ai_matches"))
    total_matches = total_result.fetchone()[0]
    
    # Average match score
    avg_result = db.execute(text("SELECT AVG(match_score) FROM ai_matches"))
    avg_score = avg_result.fetchone()[0] or 0
    
    # Fit distribution
    fit_result = db.execute(
        text("""
        SELECT overall_fit, COUNT(*) as count
        FROM ai_matches
        GROUP BY overall_fit
        ORDER BY count DESC
        """)
    )
    fit_distribution = [{"fit": row[0], "count": row[1]} for row in fit_result.fetchall()]
    
    # Recent matches (last 7 days)
    recent_result = db.execute(
        text("""
        SELECT COUNT(*) FROM ai_matches
        WHERE created_at >= NOW() - INTERVAL '7 days'
        """)
    )
    recent_matches = recent_result.fetchone()[0]
    
    return {
        "success": True,
        "total_matches": total_matches,
        "average_match_score": round(avg_score, 2),
        "fit_distribution": fit_distribution,
        "recent_matches_7d": recent_matches
    }

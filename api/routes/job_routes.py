from datetime import datetime, date
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from sqlalchemy import text

from api.db import get_db
from api.models import Job
from api.utils.security import get_current_user

router = APIRouter()

# =========================================================
# JOB MODELS
# =========================================================

class JobCreate(BaseModel):
    job_title: str
    client_name: Optional[str] = None
    location: Optional[str] = None
    work_authorization: Optional[str] = "Any"
    experience: Optional[str] = None
    salary: Optional[str] = None
    employment_type: Optional[str] = "Contract"
    visa_transfer: Optional[str] = "No"
    job_description: Optional[str] = None
    skills: Optional[str] = None

class JobUpdate(BaseModel):
    job_title: Optional[str] = None
    client_name: Optional[str] = None
    location: Optional[str] = None
    work_authorization: Optional[str] = None
    experience: Optional[str] = None
    salary: Optional[str] = None
    employment_type: Optional[str] = None
    visa_transfer: Optional[str] = None
    job_description: Optional[str] = None
    skills: Optional[str] = None

# =========================================================
# CREATE JOB
# =========================================================

@router.post("/jobs")
def create_job(
    job: JobCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new job posting"""
    
    job_id = str(uuid.uuid4())[:8].upper()
    
    db_job = Job(
        jobid=job_id,
        created_date=date.today(),
        job_title=job.job_title,
        job_description=job.job_description,
        location=job.location,
        experience=job.experience,
        skills=job.skills,
        employment_type=job.employment_type or "Full-time",
        salary=job.salary or "Negotiable",
        created_at=datetime.utcnow(),
        client_name=job.client_name or "Internal",
        work_authorization=job.work_authorization or "Any",
        visa_transfer=job.visa_transfer or "No",
        posted_by=current_user.get("email", "system")
    )
    
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    
    return {
        "success": True,
        "message": "Job created successfully",
        "job": {
            "jobid": db_job.jobid,
            "job_title": db_job.job_title,
            "location": db_job.location,
            "salary": db_job.salary,
            "employment_type": db_job.employment_type,
            "client_name": db_job.client_name,
            "created_at": db_job.created_at
        }
    }

# =========================================================
# GET ALL JOBS
# =========================================================

@router.get("/jobs")
def get_all_jobs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    location: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get all jobs with pagination and filters"""
    
    offset = (page - 1) * limit
    
    # Build query dynamically
    query = """
        SELECT 
            jobid,
            job_title,
            client_name,
            location,
            employment_type,
            salary,
            experience,
            skills,
            created_at,
            applicants_count
        FROM job_postings
        WHERE 1=1
    """
    
    params = {"limit": limit, "offset": offset}
    
    if location:
        query += " AND LOWER(location) LIKE :location"
        params["location"] = f"%{location.lower()}%"
    
    if job_type:
        query += " AND LOWER(employment_type) LIKE :job_type"
        params["job_type"] = f"%{job_type.lower()}%"
    
    if search:
        query += """ AND (
            LOWER(job_title) LIKE :search 
            OR LOWER(job_description) LIKE :search
            OR LOWER(skills) LIKE :search
        )"""
        params["search"] = f"%{search.lower()}%"
    
    # Get total count
    count_query = query.replace("SELECT \n            jobid,\n            job_title,\n            client_name,\n            location,\n            employment_type,\n            salary,\n            experience,\n            skills,\n            created_at,\n            applicants_count", "SELECT COUNT(*)")
    count_result = db.execute(text(count_query), {k: v for k, v in params.items() if k not in ["limit", "offset"]})
    total = count_result.fetchone()[0]
    
    query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    
    result = db.execute(text(query), params)
    
    jobs = []
    for row in result.fetchall():
        jobs.append({
            "jobid": row.jobid,
            "job_title": row.job_title,
            "client_name": row.client_name,
            "location": row.location,
            "employment_type": row.employment_type,
            "salary": row.salary,
            "experience": row.experience,
            "skills": row.skills,
            "created_at": row.created_at,
            "applicants_count": row.applicants_count or 0
        })
    
    return {
        "success": True,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
        "jobs": jobs
    }

# =========================================================
# GET JOB BY ID
# =========================================================

@router.get("/jobs/{job_id}")
def get_job_by_id(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific job by ID"""
    
    result = db.execute(
        text("""
        SELECT 
            jobid,
            job_title,
            job_description,
            client_name,
            location,
            experience,
            skills,
            employment_type,
            salary,
            work_authorization,
            visa_transfer,
            created_at,
            applicants_count,
            posted_by
        FROM job_postings
        WHERE jobid = :job_id
        """),
        {"job_id": job_id}
    )
    
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "success": True,
        "job": {
            "jobid": row.jobid,
            "job_title": row.job_title,
            "job_description": row.job_description,
            "client_name": row.client_name,
            "location": row.location,
            "experience": row.experience,
            "skills": row.skills,
            "employment_type": row.employment_type,
            "salary": row.salary,
            "work_authorization": row.work_authorization,
            "visa_transfer": row.visa_transfer,
            "created_at": row.created_at,
            "applicants_count": row.applicants_count or 0,
            "posted_by": row.posted_by
        }
    }

# =========================================================
# UPDATE JOB
# =========================================================

@router.put("/jobs/{job_id}")
def update_job(
    job_id: str,
    job: JobUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a job posting"""
    
    # Check if job exists
    check_result = db.execute(
        text("SELECT jobid, posted_by FROM job_postings WHERE jobid = :job_id"),
        {"job_id": job_id}
    )
    existing = check_result.fetchone()
    
    if not existing:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Build update query dynamically
    update_fields = []
    params = {"job_id": job_id}
    
    if job.job_title is not None:
        update_fields.append("job_title = :job_title")
        params["job_title"] = job.job_title
    
    if job.client_name is not None:
        update_fields.append("client_name = :client_name")
        params["client_name"] = job.client_name
    
    if job.location is not None:
        update_fields.append("location = :location")
        params["location"] = job.location
    
    if job.work_authorization is not None:
        update_fields.append("work_authorization = :work_authorization")
        params["work_authorization"] = job.work_authorization
    
    if job.experience is not None:
        update_fields.append("experience = :experience")
        params["experience"] = job.experience
    
    if job.salary is not None:
        update_fields.append("salary = :salary")
        params["salary"] = job.salary
    
    if job.employment_type is not None:
        update_fields.append("employment_type = :employment_type")
        params["employment_type"] = job.employment_type
    
    if job.visa_transfer is not None:
        update_fields.append("visa_transfer = :visa_transfer")
        params["visa_transfer"] = job.visa_transfer
    
    if job.job_description is not None:
        update_fields.append("job_description = :job_description")
        params["job_description"] = job.job_description
    
    if job.skills is not None:
        update_fields.append("skills = :skills")
        params["skills"] = job.skills
    
    if not update_fields:
        return {"success": True, "message": "No fields to update"}
    
    update_fields.append("updated_at = NOW()")
    
    query = f"""
        UPDATE job_postings
        SET {', '.join(update_fields)}
        WHERE jobid = :job_id
    """
    
    db.execute(text(query), params)
    db.commit()
    
    return {
        "success": True,
        "message": "Job updated successfully"
    }

# =========================================================
# DELETE JOB
# =========================================================

@router.delete("/jobs/{job_id}")
def delete_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a job posting"""
    
    result = db.execute(
        text("DELETE FROM job_postings WHERE jobid = :job_id RETURNING jobid"),
        {"job_id": job_id}
    )
    
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Job not found")
    
    db.commit()
    
    return {
        "success": True,
        "message": "Job deleted successfully"
    }

# =========================================================
# RECENT JOBS
# =========================================================

@router.get("/jobs/recent")
def get_recent_jobs(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get recent job postings"""
    
    jobs = (
        db.query(Job)
        .order_by(Job.created_at.desc())
        .limit(limit)
        .all()
    )
    
    result = []
    
    for job in jobs:
        result.append({
            "jobid": job.jobid,
            "job_title": job.job_title,
            "location": job.location,
            "salary": job.salary,
            "employment_type": job.employment_type,
            "client_name": job.client_name,
            "created_at": job.created_at,
            "applicants_count": 0  # Would come from applications table
        })
    
    return {
        "success": True,
        "jobs": result
    }

# =========================================================
# SEARCH JOBS
# =========================================================

@router.get("/jobs/search")
def search_jobs(
    q: str = Query(..., description="Search query"),
    location: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Search jobs by query string"""
    
    offset = (page - 1) * limit
    
    # Parse search terms
    search_terms = [t.strip().lower() for t in q.split() if t.strip()]
    
    query = """
        SELECT 
            jobid,
            job_title,
            client_name,
            location,
            employment_type,
            salary,
            experience,
            skills,
            job_description,
            created_at
        FROM job_postings
        WHERE 1=1
    """
    
    params = {"limit": limit, "offset": offset}
    
    # Add search conditions
    if search_terms:
        search_conditions = []
        for i, term in enumerate(search_terms):
            param_name = f"term_{i}"
            search_conditions.append(f"""
                (LOWER(job_title) LIKE :{param_name} 
                OR LOWER(skills) LIKE :{param_name}
                OR LOWER(job_description) LIKE :{param_name}
                OR LOWER(client_name) LIKE :{param_name})
            """)
            params[param_name] = f"%{term}%"
        
        query += " AND (" + " OR ".join(search_conditions) + ")"
    
    if location:
        query += " AND LOWER(location) LIKE :location"
        params["location"] = f"%{location.lower()}%"
    
    if job_type:
        query += " AND LOWER(employment_type) LIKE :job_type"
        params["job_type"] = f"%{job_type.lower()}%"
    
    # Get total count
    count_query = query.replace("SELECT \n            jobid,\n            job_title,\n            client_name,\n            location,\n            employment_type,\n            salary,\n            experience,\n            skills,\n            job_description,\n            created_at", "SELECT COUNT(*)")
    count_result = db.execute(text(count_query), {k: v for k, v in params.items() if k not in ["limit", "offset"]})
    total = count_result.fetchone()[0]
    
    query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    
    result = db.execute(text(query), params)
    
    jobs = []
    for row in result.fetchall():
        # Calculate relevance score
        relevance = 0
        job_text = f"{row.job_title} {row.skills} {row.job_description}".lower()
        for term in search_terms:
            relevance += job_text.count(term)
        
        jobs.append({
            "jobid": row.jobid,
            "job_title": row.job_title,
            "client_name": row.client_name,
            "location": row.location,
            "employment_type": row.employment_type,
            "salary": row.salary,
            "experience": row.experience,
            "skills": row.skills,
            "created_at": row.created_at,
            "relevance_score": relevance
        })
    
    # Sort by relevance
    jobs.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    return {
        "success": True,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
        "jobs": jobs
    }

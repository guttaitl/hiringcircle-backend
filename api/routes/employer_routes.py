from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from pydantic import BaseModel
import uuid
from datetime import date
import logging
import json
import os

from api.utils.ai_job_description import generate_structured_job_content
from api.utils.email_sender import send_job_notification, generate_ai_responsibilities
from api.db import get_db
from api.utils.security import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

# =========================================================
# JOB REQUEST MODEL
# =========================================================

class PostJobRequest(BaseModel):
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
    responsibilities: Optional[str] = None


# =========================================================
# GET EMPLOYER JOBS
# =========================================================

@router.get("/employer/jobs")
def get_employer_jobs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    user_email = current_user.get("email")
    offset = (page - 1) * limit

    result = db.execute(
        text("""
        SELECT
            jobid,
            job_title,
            client_name,
            location,
            employment_type,
            created_at
        FROM job_postings
        WHERE posted_by = :email
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
        """),
        {
            "email": user_email,
            "limit": limit,
            "offset": offset
        }
    )

    jobs = []

    for row in result.fetchall():
        jobs.append({
            "jobid": row.jobid,
            "job_title": row.job_title,
            "client_name": row.client_name,
            "location": row.location,
            "employment_type": row.employment_type,
            "created_at": row.created_at
        })

    return {
        "success": True,
        "jobs": jobs
    }


@router.post("/post-job")
async def post_job(
    request: PostJobRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    import uuid

    user_email = current_user.get("email")

    # =====================================================
    # USER INFO
    # =====================================================
    user_result = db.execute(
        text("""
        SELECT full_name, company 
        FROM usersdata 
        WHERE email = :email
        LIMIT 1
        """),
        {"email": user_email}
    ).fetchone()

    if user_result:
        user_company = user_result.company or user_email.split('@')[1].split('.')[0].upper()
    else:
        domain = user_email.split('@')[1]
        user_company = domain.split('.')[0].upper()

    if request.client_name:
        user_company = request.client_name.upper()

    # =====================================================
    # JOB ID
    # =====================================================
    job_public_id = str(uuid.uuid4())[:8].upper()

    job_description = request.job_description
    skills = request.skills

    # =====================================================
    # RESPONSIBILITIES (AI ONLY)
    # =====================================================
    responsibilities = request.responsibilities or ""

    if not responsibilities:
        try:
            ai_resp = generate_ai_responsibilities(
                role=request.job_title,
                skills=skills or "",
                experience=request.experience or ""
            )

            if ai_resp:
                responsibilities = "\n".join(ai_resp)
            else:
                responsibilities = ""

        except Exception as e:
            logger.error(f"AI responsibility generation failed: {e}")
            responsibilities = ""

    # =====================================================
    # AI GENERATION
    # =====================================================
    if not job_description or not skills:
        try:
            ai_json = generate_structured_job_content(
                job_title=request.job_title,
                experience=request.experience,
                company_name=None,
                location=request.location,
                employment_type=request.employment_type
            )

            data = json.loads(ai_json)

            if not skills:
                skills = "\n".join(data.get("required_skills", []))

            if not job_description:
                job_description = data.get("description")

        except Exception:
            job_description = job_description or f"Seeking {request.job_title}"
            skills = skills or "Communication\nTeamwork"

    # =====================================================
    # INSERT JOB
    # =====================================================
    try:
        result = db.execute(
            text("""
            INSERT INTO job_postings (
                jobid, created_date, job_title, client_name, location,
                work_authorization, experience, salary, employment_type,
                visa_transfer, job_description, skills, responsibilities, posted_by, created_at
            ) VALUES (
                :jobid, :created_date, :job_title, :client_name, :location,
                :work_authorization, :experience, :salary, :employment_type,
                :visa_transfer, :job_description, :skills, :responsibilities, :posted_by, NOW()
            )
            RETURNING jobid
            """),
            {
                "jobid": job_public_id,
                "created_date": date.today(),
                "job_title": request.job_title,
                "client_name": request.client_name or "Direct Client",
                "location": request.location or "Remote",
                "work_authorization": request.work_authorization,
                "experience": request.experience or "Not specified",
                "salary": request.salary or "Competitive",
                "employment_type": request.employment_type,
                "visa_transfer": request.visa_transfer,
                "job_description": job_description,
                "skills": skills,
                "responsibilities": responsibilities,
                "posted_by": user_email
            }
        )

        job_row = result.fetchone()
        db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Job insert failed: {e}")
        return {
            "success": False,
            "error": "Job creation failed"
        }

    # =====================================================
    # MATCHING QUEUE
    # =====================================================
    try:
        db.execute(
            text("""
            INSERT INTO job_matching_queue (
                jobid, job_title, job_description,
                poster_email, status, attempts, created_at
            )
            VALUES (
                :jobid, :title, :jd,
                :email, 'PENDING', 0, NOW()
            )
            """),
            {
                "jobid": job_public_id,
                "title": request.job_title,
                "jd": job_description,
                "email": user_email
            }
        )
        db.commit()
    except Exception as e:
        logger.warning(f"Queue insert failed: {e}")

    # =====================================================
    # EMAIL (NON-BLOCKING)
    # =====================================================
    try:
        background_tasks.add_task(
            send_job_notification,
            {
                "job_title": request.job_title,
                "poster_company": user_company,
                "location": request.location or "Remote",
                "job_description": job_description,
                "skills": skills,
                "responsibilities": responsibilities,
                "jobid": job_public_id,
                "employment_type": request.employment_type
            }
        )
    except Exception as e:
        logger.error(f"Email task failed: {e}")

    # =====================================================
    # ✅ FINAL RETURN (CRITICAL FIX)
    # =====================================================
    return {
        "success": True,
        "jobid": job_public_id
    }

# =========================================================
# GET SINGLE JOB
# =========================================================

@router.get("/employer/jobs/{job_id}")
def get_job_details(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    
    user_email = current_user.get("email")
    
    result = db.execute(
        text("""
        SELECT jobid, job_title, client_name, location, work_authorization,
               experience, salary, employment_type, visa_transfer,
               job_description, skills, created_at
        FROM job_postings
        WHERE jobid = :jobid AND posted_by = :email
        """),
        {"jobid": job_id, "email": user_email}
    ).fetchone()
    
    if not result:
        return {"success": False, "message": "Job not found"}
    
    return {
        "success": True,
        "job": {
            "jobid": result.jobid,
            "job_title": result.job_title,
            "client_name": result.client_name,
            "location": result.location,
            "work_authorization": result.work_authorization,
            "experience": result.experience,
            "salary": result.salary,
            "employment_type": result.employment_type,
            "visa_transfer": result.visa_transfer,
            "job_description": result.job_description,
            "skills": result.skills,
            "created_at": result.created_at
        }
    }


# =========================================================
# DASHBOARD STATS - ONLY THIS ONE, AT THE BOTTOM
# =========================================================

@router.get("/employer/dashboard/stats")
def get_employer_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    user_email = current_user.get("email")

    total_jobs = db.execute(
        text("""
        SELECT COUNT(*) FROM job_postings
        WHERE posted_by = :email
        """),
        {"email": user_email}
    ).scalar()

    active_jobs = db.execute(
        text("""
        SELECT COUNT(*) FROM job_postings
        WHERE posted_by = :email
        AND created_at >= NOW() - INTERVAL '30 days'
        """),
        {"email": user_email}
    ).scalar()

    total_applicants = db.execute(
        text("""
        SELECT COUNT(*)
        FROM job_applications ja
        JOIN job_postings jp ON ja.job_id = jp.jobid
        WHERE jp.posted_by = :email
        """),
        {"email": user_email}
    ).scalar()

    # GET RECENT JOBS WITH APPLICANT COUNTS
    recent_jobs_result = db.execute(
        text("""
        SELECT 
            jp.jobid,
            jp.job_title,
            jp.client_name,
            jp.location,
            jp.employment_type,
            jp.created_at,
            COUNT(ja.id) as applicants_count
        FROM job_postings jp
        LEFT JOIN job_applications ja ON ja.job_id = jp.jobid
        WHERE jp.posted_by = :email
        GROUP BY jp.jobid, jp.job_title, jp.client_name, jp.location, jp.employment_type, jp.created_at
        ORDER BY jp.created_at DESC
        LIMIT 10
        """),
        {"email": user_email}
    )

    recent_jobs = []
    for row in recent_jobs_result.fetchall():
        recent_jobs.append({
            "jobid": row.jobid,
            "job_title": row.job_title,
            "client_name": row.client_name,
            "location": row.location,
            "employment_type": row.employment_type,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "applicants_count": row.applicants_count or 0
        })

    return {
        "success": True,
        "stats": {
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "total_applicants": total_applicants
        },
        "recent_jobs": recent_jobs
    }

# =========================================================
# DELETE JOB
# =========================================================

@router.delete("/employer/jobs/{job_id}")
def delete_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    
    user_email = current_user.get("email")
    
    try:
        # First verify the job belongs to this user
        check = db.execute(
            text("""
            SELECT jobid FROM job_postings 
            WHERE jobid = :jobid AND posted_by = :email
            """),
            {"jobid": job_id, "email": user_email}
        ).fetchone()
        
        if not check:
            return {"success": False, "message": "Job not found or unauthorized"}
        
        # Delete related applications first (if foreign key constraints exist)
        db.execute(
            text("""
            DELETE FROM job_applications 
            WHERE job_id = :jobid
            """),
            {"jobid": job_id}
        )
        
        # Delete the job
        result = db.execute(
            text("""
            DELETE FROM job_postings 
            WHERE jobid = :jobid AND posted_by = :email
            """),
            {"jobid": job_id, "email": user_email}
        )
        
        db.commit()
        
        if result.rowcount == 0:
            return {"success": False, "message": "Job not found"}
        
        logger.info(f"Job {job_id} deleted by {user_email}")
        return {"success": True, "message": "Job deleted successfully"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Delete error: {e}")
        return {"success": False, "message": f"Failed to delete job: {str(e)}"}
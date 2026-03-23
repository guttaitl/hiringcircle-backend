from datetime import datetime, date
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import text

from api.db import get_db
from api.models import Job
from api.utils.security import get_current_user

router = APIRouter()

# =========================================================
# MODELS
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

    return {"success": True, "job": db_job.jobid}


# =========================================================
# RECENT JOBS (🔥 MUST BE BEFORE {job_id})
# =========================================================

@router.get("/jobs/recent")
def get_recent_jobs(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    jobs = (
        db.query(Job)
        .order_by(Job.created_at.desc())
        .limit(limit)
        .all()
    )

    return {
        "success": True,
        "jobs": [
            {
                "jobid": j.jobid,
                "job_title": j.job_title,
                "location": j.location,
                "salary": j.salary,
                "employment_type": j.employment_type,
                "client_name": j.client_name,
                "created_at": j.created_at,
                "applicants_count": 0
            }
            for j in jobs
        ]
    }


# =========================================================
# GET ALL JOBS
# =========================================================

@router.get("/jobs")
def get_all_jobs(
    db: Session = Depends(get_db)
):
    jobs = db.query(Job).all()
    return {"success": True, "jobs": jobs}


# =========================================================
# GET JOB BY ID (🔥 MUST BE LAST)
# =========================================================

@router.get("/jobs/{job_id}")
def get_job_by_id(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.jobid == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {"success": True, "job": job}


# =========================================================
# UPDATE JOB
# =========================================================

@router.put("/jobs/{job_id}")
def update_job(
    job_id: str,
    job: JobUpdate,
    db: Session = Depends(get_db)
):
    existing = db.query(Job).filter(Job.jobid == job_id).first()

    if not existing:
        raise HTTPException(status_code=404, detail="Job not found")

    for field, value in job.dict(exclude_unset=True).items():
        setattr(existing, field, value)

    db.commit()

    return {"success": True}


# =========================================================
# DELETE JOB
# =========================================================

@router.delete("/jobs/{job_id}")
def delete_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.jobid == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    db.delete(job)
    db.commit()

    return {"success": True}
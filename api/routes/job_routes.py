print("🔥 JOB ROUTES UPDATED Version 2")
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
from api.job_distribution import auto_distribute_job

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
    try:
        import uuid
        from datetime import date, datetime

        # 🔥 Generate Job ID
        job_id = str(uuid.uuid4())[:8].upper()

        # 🔥 Save to DB
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

        # 🔥 Build job data for distribution
        job_data = {
            "jobid": db_job.jobid,
            "job_title": db_job.job_title,
            "location": db_job.location,
            "job_description": db_job.job_description,
            "skills": db_job.skills,
            "employment_type": db_job.employment_type,
            "salary": db_job.salary,
            "experience": db_job.experience,
            "work_authorization": db_job.work_authorization,
            "visa_transfer": db_job.visa_transfer,
            "user_email": db_job.posted_by,
            "user_company": db_job.client_name
        }

        # 🔥 CALL DISTRIBUTION ENGINE (SAFE)
        try:
            distribution = auto_distribute_job(job_data, db)
        except Exception as dist_err:
            print("⚠️ Distribution failed:", dist_err)
            distribution = {
                "results": [],
                "error": str(dist_err)
            }

        # 🔥 FINAL RESPONSE (frontend-safe)
        return {
            "success": True,
            "jobid": db_job.jobid,
            "distribution": distribution or {"results": []}
        }

    except Exception as e:
        import traceback
        print("❌ ERROR IN /api/jobs")
        print(traceback.format_exc())

        raise HTTPException(
            status_code=500,
            detail="Job creation failed"
        )
    
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
    offset = (page - 1) * limit

    query = """
        SELECT jobid, job_title, client_name, location,
               employment_type, salary, experience,
               skills, created_at, applicants_count
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

    count_query = query.replace(
        "SELECT jobid, job_title, client_name, location, employment_type, salary, experience, skills, created_at, applicants_count",
        "SELECT COUNT(*)"
    )

    total = db.execute(text(count_query), {k: v for k, v in params.items() if k not in ["limit", "offset"]}).fetchone()[0]

    query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    rows = db.execute(text(query), params).fetchall()

    return {
        "success": True,
        "total": total,
        "jobs": [dict(row._mapping) for row in rows]
    }


# =========================================================
# RECENT JOBS ✅ (MOVED UP)
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
# SEARCH JOBS
# =========================================================

@router.get("/jobs/search")
def search_jobs(
    q: str,
    db: Session = Depends(get_db)
):
    query = """
        SELECT jobid, job_title, location, skills, created_at
        FROM job_postings
        WHERE LOWER(job_title) LIKE :q OR LOWER(skills) LIKE :q
    """

    rows = db.execute(text(query), {"q": f"%{q.lower()}%"}).fetchall()

    return {"success": True, "jobs": [dict(r._mapping) for r in rows]}


# =========================================================
# GET JOB BY ID ❌ (MUST BE LAST)
# =========================================================

@router.get("/jobs/{job_id}")
def get_job_by_id(job_id: str, db: Session = Depends(get_db)):
    row = db.execute(
        text("SELECT * FROM job_postings WHERE jobid = :job_id"),
        {"job_id": job_id}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Job not found")

    return {"success": True, "job": dict(row._mapping)}


# =========================================================
# UPDATE JOB
# =========================================================

@router.put("/jobs/{job_id}")
def update_job(job_id: str, job: JobUpdate, db: Session = Depends(get_db)):
    fields = []
    params = {"job_id": job_id}

    for k, v in job.dict(exclude_unset=True).items():
        fields.append(f"{k} = :{k}")
        params[k] = v

    if not fields:
        return {"success": True}

    query = f"UPDATE job_postings SET {', '.join(fields)} WHERE jobid = :job_id"

    db.execute(text(query), params)
    db.commit()

    return {"success": True}


# =========================================================
# DELETE JOB
# =========================================================

@router.delete("/jobs/{job_id}")
def delete_job(job_id: str, db: Session = Depends(get_db)):
    res = db.execute(
        text("DELETE FROM job_postings WHERE jobid = :job_id RETURNING jobid"),
        {"job_id": job_id}
    )

    if not res.fetchone():
        raise HTTPException(status_code=404, detail="Job not found")

    db.commit()

    return {"success": True}
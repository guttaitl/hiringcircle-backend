from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from api.db import get_db

router = APIRouter()


# CREATE JOB
@router.post("/jobs")
def create_job(payload: dict, db: Session = Depends(get_db)):

    db.execute(
        text("""
        INSERT INTO job_postings
        (
            job_title,
            client_name,
            location,
            job_description,
            created_date
        )
        VALUES
        (
            :title,
            :client_name,
            :location,
            :description,
            NOW()
        )
        """),
        payload
    )

    db.commit()

    return {"status": "success"}


# GET RECENT JOBS
@router.get("/jobs/recent")
def get_recent_jobs(db: Session = Depends(get_db)):
    try:
        jobs = (
            db.query(Job)
            .order_by(Job.created_at.desc())
            .limit(5)
            .all()
        )

        return {
            "success": True,
            "jobs": jobs
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from api.db import get_db
import logging

# IMPORT DISTRIBUTION FUNCTIONS
from api.job_distribution import auto_distribute_with_linkedin_draft, JobDistributor

router = APIRouter()
logger = logging.getLogger(__name__)


# CREATE JOB WITH AUTO-DISTRIBUTION
@router.post("/post-job")
async def create_job(payload: dict, db: Session = Depends(get_db)):
    """
    Create a new job posting and auto-distribute to job portals.
    Returns job ID and distribution results including LinkedIn draft.
    """
    try:
        # STEP 1: INSERT JOB INTO DATABASE
        result = db.execute(
            text("""
                INSERT INTO job_postings
                (job_title, client_name, location, job_description, 
                 work_authorization, experience, salary, employment_type, 
                 visa_transfer, skills, created_date, user_email, user_company)
                VALUES
                (:job_title, :client_name, :location, :job_description,
                 :work_authorization, :experience, :salary, :employment_type,
                 :visa_transfer, :skills, NOW(), :user_email, :user_company)
            """),
            {
                "job_title": payload.get("job_title"),
                "client_name": payload.get("client_name"),
                "location": payload.get("location"),
                "job_description": payload.get("job_description"),
                "work_authorization": payload.get("work_authorization", "Any"),
                "experience": payload.get("experience"),
                "salary": payload.get("salary"),
                "employment_type": payload.get("employment_type", "Contract"),
                "visa_transfer": payload.get("visa_transfer", "No"),
                "skills": payload.get("skills"),
                "user_email": payload.get("user_email", "admin@hiringcircle.us"),
                "user_company": payload.get("user_company", "HiringCircle")
            }
        )

        db.commit()

        # Get the inserted job ID
        job_id = result.lastrowid

        # Prepare job data for distribution
        job = {
            "jobid": str(job_id),
            "job_title": payload.get("job_title"),
            "client_name": payload.get("client_name"),
            "location": payload.get("location"),
            "job_description": payload.get("job_description"),
            "work_authorization": payload.get("work_authorization", "Any"),
            "experience": payload.get("experience"),
            "salary": payload.get("salary"),
            "employment_type": payload.get("employment_type", "Contract"),
            "visa_transfer": payload.get("visa_transfer", "No"),
            "skills": payload.get("skills"),
            "user_email": payload.get("user_email", "admin@hiringcircle.us"),
            "user_company": payload.get("user_company", "HiringCircle")
        }

        # STEP 2: AUTO-DISTRIBUTE TO JOB PORTALS (WITH LINKEDIN DRAFT)
        distribution_results = None
        try:
            logger.info(f"Starting auto-distribution for job {job_id}")

            # Use LinkedIn Draft mode (opens LinkedIn with pre-filled content)
            # Set use_api=True if you have LinkedIn API credentials configured
            distribution_results = auto_distribute_with_linkedin_draft(job, db, use_api=False)

            logger.info(f"Distribution complete: {distribution_results['summary']}")

        except Exception as dist_error:
            logger.error(f"Distribution failed (non-blocking): {dist_error}")
            distribution_results = {
                "success": False,
                "error": str(dist_error),
                "summary": {"total": 0, "posted": 0, "failed": 0, "skipped": 0},
                "results": []
            }

        # STEP 3: RETURN SUCCESS WITH DISTRIBUTION INFO
        return {
            "success": True,
            "jobid": str(job_id),
            "message": "Job posted successfully",
            "distribution": distribution_results
        }

    except Exception as e:
        logger.error(f"Job creation failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# GET RECENT JOBS
@router.get("/jobs/recent")
def get_recent_jobs(db: Session = Depends(get_db)):
    """Get recent job postings."""
    try:
        from api.models import Job
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


# CHECK DISTRIBUTION STATUS
@router.get("/distribution-status")
def get_distribution_status():
    """Check which job portals are configured and ready."""
    from api.job_distribution import validate_portal_config

    try:
        status = validate_portal_config()
        ready_count = sum(1 for s in status.values() if s.get('ready'))

        return {
            "success": True,
            "portals": status,
            "ready_count": ready_count,
            "message": f"{ready_count} portals ready for auto-posting"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

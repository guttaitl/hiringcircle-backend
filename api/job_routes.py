from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from api.db import get_db
import logging

# ADD THIS IMPORT
from job_distribution import auto_distribute_job, JobDistributor

router = APIRouter()
logger = logging.getLogger(__name__)


# CREATE JOB WITH AUTO-DISTRIBUTION
@router.post("/post-job")
async def create_job(payload: dict, db: Session = Depends(get_db)):
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
        
        # STEP 2: AUTO-DISTRIBUTE TO JOB PORTALS
        distribution_results = None
        try:
            logger.info(f"Starting auto-distribution for job {job_id}")
            distribution_results = auto_distribute_job(job, db)
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
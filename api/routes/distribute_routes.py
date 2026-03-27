from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from api.db import get_db
from api.job_distribution import JobDistributor, validate_portal_config, auto_distribute_job
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/distribute-job")
async def distribute_job(payload: dict, db: Session = Depends(get_db)):
    """
    Standalone endpoint to distribute an existing job to portals
    """
    try:
        job_id = payload.get("job_id")
        portals = payload.get("portals")  # Optional: specific portals
        
        if not job_id:
            raise HTTPException(status_code=400, detail="job_id required")
        
        # Fetch job from database (implement based on your schema)
        # This is a placeholder - replace with your actual query
        job = {
            "jobid": job_id,
            "job_title": payload.get("job_title", ""),
            "location": payload.get("location", ""),
            "job_description": payload.get("job_description", ""),
            "skills": payload.get("skills", ""),
            "employment_type": payload.get("employment_type", "Contract"),
            "salary": payload.get("salary", ""),
            "experience": payload.get("experience", ""),
            "work_authorization": payload.get("work_authorization", "Any"),
            "visa_transfer": payload.get("visa_transfer", "No"),
            "user_email": payload.get("user_email", "admin@hiringcircle.us"),
            "user_company": payload.get("user_company", "HiringCircle")
        }
        
        # Distribute
        if portals:
            distributor = JobDistributor(db)
            results = distributor.distribute_job(job, portals=portals)
        else:
            results = auto_distribute_job(job, db)
        
        return results
        
    except Exception as e:
        logger.error(f"Distribution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/distribution-status")
async def distribution_status():
    """Check which portals are configured"""
    return validate_portal_config()
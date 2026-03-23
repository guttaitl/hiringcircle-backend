from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.db import get_db_conn
from api.auth_routes import get_current_user

router = APIRouter()

class JobPostRequest(BaseModel):
    title: str
    description: str

# ------------------------------------------------
# POST JOB
# ------------------------------------------------
@router.post("/post-job")
def post_job(payload: JobPostRequest, user=Depends(get_current_user)):

    if user["role"] != "EMPLOYER":
        raise HTTPException(403, "Employer only")

    conn = get_db_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO job_postings
        (job_title,job_description,posted_by)
        VALUES (%s,%s,%s)
    """, (
        payload.title,
        payload.description,
        user["email"]
    ))

    conn.commit()
    cur.close()
    conn.close()

    return {"message": "Job posted"}
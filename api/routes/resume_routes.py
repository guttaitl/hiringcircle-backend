import os
import shutil
import uuid
import hashlib
import json
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from api.db import get_db

router = APIRouter()

# =========================================================
# UPLOAD RESUME
# =========================================================

@router.post("/resumes/upload")
async def upload_resume(
    file: UploadFile = File(...),
    profile: str = Form(...),
    user_id: str = Form(...),
    job_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Upload resume and store metadata
    """

    try:

        # Parse profile JSON
        profile_data = json.loads(profile)

        # --------------------------------------------------
        # CREATE UPLOAD DIRECTORY
        # --------------------------------------------------

        upload_dir = "uploads/resumes"
        os.makedirs(upload_dir, exist_ok=True)

        # --------------------------------------------------
        # GENERATE FILE NAME
        # --------------------------------------------------

        resume_id = str(uuid.uuid4())

        filename = f"{resume_id}_{file.filename}"

        filepath = os.path.join(upload_dir, filename).replace("\\", "/")

        # --------------------------------------------------
        # SAVE FILE
        # --------------------------------------------------

        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # --------------------------------------------------
        # GENERATE FILE HASH (FOR DUPLICATE DETECTION)
        # --------------------------------------------------

        with open(filepath, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        # --------------------------------------------------
        # INSERT INTO candidate_resumes
        # --------------------------------------------------

        db.execute(
            text("""
            INSERT INTO candidate_resumes (
                id,
                user_id,
                file_path,
                original_file_name,
                resume_hash,
                created_at
            )
            VALUES (
                :id,
                :user_id,
                :file_path,
                :original_file_name,
                :resume_hash,
                NOW()
            )
            """),
            {
                "id": resume_id,
                "user_id": user_id,
                "file_path": filepath,
                "original_file_name": file.filename,
                "resume_hash": file_hash
            }
        )

        # --------------------------------------------------
        # ADD TO JOB MATCHING QUEUE
        # --------------------------------------------------

        db.execute(
            text("""
            INSERT INTO job_matching_queue (
                resume_id,
                created_at
            )
            VALUES (
                :resume_id,
                NOW()
            )
            """),
            {
                "resume_id": resume_id
            }
        )

        db.commit()

        return {
            "success": True,
            "resume_id": resume_id,
            "file": filename
        }

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# SEARCH RESUMES
# =========================================================

@router.get("/resumes/search")
def search_resumes(
    q: str,
    db: Session = Depends(get_db)
):

    result = db.execute(
        text("""
        SELECT id,
               user_id,
               file_path,
               created_at
        FROM candidate_resumes
        WHERE resume_text ILIKE :query
        ORDER BY created_at DESC
        LIMIT 50
        """),
        {"query": f"%{q}%"}
    )

    rows = result.fetchall()

    return {
        "success": True,
        "count": len(rows),
        "results": [dict(r._mapping) for r in rows]
    }

# =========================================================
# GET RESUME
# =========================================================

@router.get("/resumes/{resume_id}")
def get_resume(
    resume_id: str,
    db: Session = Depends(get_db)
):

    result = db.execute(
        text("""
        SELECT *
        FROM candidate_resumes
        WHERE id = :id
        """),
        {"id": resume_id}
    )

    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Resume not found")

    return {
        "success": True,
        "resume": dict(row._mapping)
    }


# =========================================================
# LIST RESUMES
# =========================================================

@router.get("/resumes")
def list_resumes(
    db: Session = Depends(get_db)
):

    result = db.execute(
        text("""
        SELECT id,
               user_id,
               file_path,
               parsed_successfully,
               created_at
        FROM candidate_resumes
        ORDER BY created_at DESC
        LIMIT 100
        """)
    )

    rows = result.fetchall()

    return {
        "success": True,
        "count": len(rows),
        "resumes": [dict(r._mapping) for r in rows]
    }
import shutil
import uuid
import hashlib
import json
import os
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from api.db import get_db

router = APIRouter()

# =========================================================
# UPLOAD RESUME (FIXED VERSION)
# =========================================================

@router.post("/resumes/upload")
async def upload_resume(
    file: UploadFile = File(...),
    profile: str = Form(...),
    user_id: str = Form(...),
    job_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    try:
        # ------------------------------------------
        # Parse profile JSON (optional use)
        # ------------------------------------------
        try:
            profile_data = json.loads(profile)
        except:
            profile_data = {}

        # ------------------------------------------
        # Directory (Railway-safe path)
        # ------------------------------------------
        upload_dir = "/app/uploads/resumes"
        os.makedirs(upload_dir, exist_ok=True)

        # ------------------------------------------
        # Unique filename
        # ------------------------------------------
        unique_id = str(uuid.uuid4())
        filename = f"{unique_id}_{file.filename}"
        filepath = os.path.join(upload_dir, filename).replace("\\", "/")

        # ------------------------------------------
        # Save file
        # ------------------------------------------
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        print(f"✅ File saved: {filepath}")

        # ------------------------------------------
        # Generate file hash (for duplicate detection)
        # ------------------------------------------
        with open(filepath, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        existing = db.execute(
            text("""
            SELECT id FROM candidate_resumes
            WHERE file_hash = :file_hash
            """),
            {"file_hash": file_hash}
        ).fetchone()

        if existing:
            return {
                "success": True,
                "resume_id": existing[0],
                "message": "Duplicate resume ignored"
            }

        # ------------------------------------------
        # Insert into candidate_resumes (FIXED)
        # ------------------------------------------
        result = db.execute(
            text("""
            INSERT INTO candidate_resumes (
                user_id,
                file_path,
                file_hash,
                parsed_successfully,
                created_at
            )
            VALUES (
                :user_id,
                :file_path,
                :file_hash,
                false,
                NOW()
            )
            RETURNING id
            """),
            {
                "user_id": user_id,
                "file_path": filepath,
                "file_hash": file_hash
            }
        )

        resume_id = result.fetchone()[0]

        # Add to job matching queue ONLY if job_id exists
        if job_id:
            db.execute(
                text("""
                INSERT INTO job_matching_queue (
                    job_id,
                    resume_id,
                    created_at
                )
                VALUES (
                    :job_id,
                    :resume_id,
                    NOW()
                )
                """),
                {
                    "job_id": job_id,
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
        print(f"❌ Upload failed: {e}")

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
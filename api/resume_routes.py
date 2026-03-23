import os
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import FileResponse
from uuid import uuid4

router = APIRouter()

UPLOAD_DIR = "uploads/resumes"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/api/resumes/upload")
async def upload_resume(file: UploadFile = File(...)):

    filename = f"{uuid4()}_{file.filename}"
    path = os.path.join(UPLOAD_DIR, filename)

    contents = await file.read()

    with open(path, "wb") as f:
        f.write(contents)

    return {"filename": filename}

@router.get("/resume/{filename}")
def get_resume(filename: str):
    return FileResponse(f"{UPLOAD_DIR}/{filename}")
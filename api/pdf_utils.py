import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

RESUME_DIR = os.getenv(
    "RESUME_DIR",
    os.path.join(BASE_DIR, "resumes")
)

os.makedirs(RESUME_DIR, exist_ok=True)


def ensure_pdf_exists(filename: str) -> str:
    """
    Ensures the resume file exists.
    - If already PDF → return path
    - If DOC/DOCX → return original file (conversion disabled on Linux servers)
    """

    input_path = os.path.join(RESUME_DIR, filename)

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Resume not found: {filename}")

    # If already PDF
    if filename.lower().endswith(".pdf"):
        return input_path

    # On Linux (PythonAnywhere) we do not convert DOC/DOCX
    # Just return original file
    return input_path
import os
from docx2pdf import convert

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESUME_DIR = os.path.join(BASE_DIR, "resumes")
PDF_DIR = os.path.join(BASE_DIR, "pdf_cache")

os.makedirs(PDF_DIR, exist_ok=True)

def get_pdf_path(docx_filename: str) -> str:
    pdf_name = os.path.splitext(docx_filename)[0] + ".pdf"
    return os.path.join(PDF_DIR, pdf_name)

def ensure_pdf_exists(docx_filename: str):
    docx_path = os.path.join(RESUME_DIR, docx_filename)
    pdf_path = get_pdf_path(docx_filename)

    if not os.path.exists(pdf_path):
        convert(docx_path, pdf_path)

    return pdf_path

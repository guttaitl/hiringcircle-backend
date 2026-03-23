import pdfplumber
import docx
from io import BytesIO


def parse_resume(file_bytes: bytes, filename: str) -> str:
    if filename.lower().endswith(".pdf"):
        text = ""
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text

    if filename.lower().endswith(".docx"):
        doc = docx.Document(BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs)

    return ""

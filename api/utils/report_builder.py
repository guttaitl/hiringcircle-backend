import os
import uuid
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from api.utils.openai_client import call_openai


# =========================================================
# CONFIG
# =========================================================

REPORTS_FOLDER = os.getenv("REPORTS_FOLDER", "./reports")
os.makedirs(REPORTS_FOLDER, exist_ok=True)


# =========================================================
# AI SKILL MATRIX (JD vs PROFILE)
# =========================================================
def generate_ai_skill_matrix(job_text: str, resume_text: str):

    if not job_text or not resume_text:
        return []

    try:
        response = call_openai(
            messages=[
                {
                    "role": "system",
                    "content": """
You are a senior technical hiring evaluator.

Extract core technical skills from the Job Description.
Compare them with the Candidate Resume.

Classify each skill as:
EXPLICIT  → Clearly stated in resume
IMPLICIT  → Strongly inferred
PARTIAL   → Mentioned but weak coverage
NO        → Not present

Return ONLY valid JSON.

FORMAT:
{
  "skills": [
    {
      "skill": "string",
      "evidence": "EXPLICIT | IMPLICIT | PARTIAL | NO",
      "required": true
    }
  ]
}
"""
                },
                {
                    "role": "user",
                    "content": f"""
JOB DESCRIPTION:
{job_text}

CANDIDATE RESUME:
{resume_text}
"""
                }
            ],
            expect_json=True
        )

        skills = response.get("skills", [])

        # defensive validation
        if not isinstance(skills, list):
            return []

        return skills

    except Exception:
        return []


# =========================================================
# MAIN REPORT BUILDER
# =========================================================
def build_basic_report(sub):

    # ----------------------------
    # SAFE FIELD EXTRACTION
    # ----------------------------
    candidate_name = (
        getattr(sub, "candidate_name", None)
        or getattr(sub, "full_name", None)
        or "Candidate"
    )

    job_id = getattr(sub, "job_id", None) or "—"
    match_score = round(float(getattr(sub, "match_score", 0)), 2)
    processed_at = getattr(sub, "processed_at", None)

    if processed_at:
        processed_at = processed_at.strftime("%Y-%m-%d %H:%M")
    else:
        processed_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M")

    job_text = getattr(sub, "job_description", "") or ""
    resume_text = getattr(sub, "resume_text", "") or ""

    # ----------------------------
    # AI Skill Matrix
    # ----------------------------
    skill_matrix = generate_ai_skill_matrix(job_text, resume_text)

    # ----------------------------
    # UNIQUE FILENAME (NO OVERWRITE)
    # ----------------------------
    safe_name = candidate_name.replace(" ", "_")
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    unique_id = str(uuid.uuid4())[:8]

    filename = f"REP_{safe_name}_{timestamp}_{unique_id}.pdf"
    path = os.path.join(REPORTS_FOLDER, filename)

    # ----------------------------
    # PDF SETUP
    # ----------------------------
    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    story = []

    header_blue = ParagraphStyle(
        "header_blue",
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=colors.HexColor("#0A66C2"),
        spaceAfter=6,
        alignment=TA_LEFT,
    )

    body = ParagraphStyle(
        "body",
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        alignment=TA_LEFT,
    )

    score_style = ParagraphStyle(
        "score",
        fontName="Helvetica-Bold",
        fontSize=22,
        alignment=TA_CENTER,
    )

    page_width = doc.width

    # ==================================================
    # HEADER TABLE
    # ==================================================
    header_table = Table(
        [
            ["Candidate Name", candidate_name,
             Paragraph(f"{match_score}%", score_style)],
            ["Job ID", job_id, ""],
            ["Processed At", processed_at, ""],
        ],
        colWidths=[page_width * 0.30, page_width * 0.50, page_width * 0.20],
    )

    header_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold"),
        ("SPAN", (2, 0), (2, 2)),
        ("ALIGN", (2, 0), (2, 2), "CENTER"),
        ("VALIGN", (2, 0), (2, 2), "MIDDLE"),
    ]))

    story.append(header_table)
    story.append(Spacer(1, 18))

    # ==================================================
    # JD SKILLS VS PROFILE
    # ==================================================
    story.append(Paragraph("JD Skills vs Candidate Profile", header_blue))
    story.append(Spacer(1, 6))

    rows = [["Skill", "Evidence", "Requirement"]]

    if skill_matrix:
        for s in skill_matrix:
            rows.append([
                s.get("skill", "—"),
                s.get("evidence", "—"),
                "Required" if s.get("required") else "Optional"
            ])
    else:
        rows.append(["No skills extracted", "—", "—"])

    table = Table(
        rows,
        colWidths=[page_width * 0.45, page_width * 0.25, page_width * 0.30],
    )

    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8F1FA")),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
    ]))

    story.append(table)
    story.append(Spacer(1, 16))

    # ==================================================
    # BUILD PDF
    # ==================================================
    doc.build(story)

    # attach path to object if present
    if hasattr(sub, "report_path"):
        sub.report_path = filename

    return path
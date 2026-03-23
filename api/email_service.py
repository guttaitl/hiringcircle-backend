"""
Email Service for Hiring Circle Platform
Handles all email notifications including job alerts, verification, and shortlist emails
"""

import os
import smtplib
import logging
import time
import mimetypes
import re
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, List, Tuple

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


# ==========================================================
# LOAD ENV
# ==========================================================
ROOT_ENV = Path(__file__).resolve().parent.parent / ".env.development"
load_dotenv(ROOT_ENV, override=False)

if os.getenv("ENVIRONMENT") == "production":
    PROD_ENV = Path(__file__).resolve().parent.parent / ".env.production"
    load_dotenv(PROD_ENV, override=True)


def require_env(value: Optional[str], name: str) -> str:
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


# ==========================================================
# CONFIG
# ==========================================================
EMAIL_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("SMTP_PORT", 587))

EMAIL_USER = os.getenv("SMTP_USER", "")
EMAIL_PASS = os.getenv("SMTP_PASSWORD", "")

EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "HiringCircle")

EMAIL_TO = os.getenv("DEFAULT_TO_EMAIL", "")
EMAIL_BCC = os.getenv("DEFAULT_BCC_EMAIL", "")

SMTP_TIMEOUT = int(os.getenv("SMTP_TIMEOUT", 20))
SMTP_RETRIES = int(os.getenv("SMTP_RETRIES", 3))

logger = logging.getLogger("email_service")


# ==========================================================
# SEND EMAIL WITH RETRY
# ==========================================================
def send_email_with_retry(msg, recipients):
    if not EMAIL_USER or not EMAIL_PASS:
        logger.warning("Email credentials not configured")
        return False

    for attempt in range(SMTP_RETRIES):
        try:
            server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=SMTP_TIMEOUT)
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)

            server.sendmail(EMAIL_USER, recipients, msg.as_string())
            server.quit()

            logger.info("Email sent successfully")
            return True

        except Exception as e:
            logger.warning(f"Email attempt {attempt+1} failed: {e}")
            time.sleep(2)

    logger.error("All email attempts failed")
    return False


# ==========================================================
# FORMAT JOB DESCRIPTION
# ==========================================================
def format_job_description_html(text: str) -> str:
    if not text:
        return ""

    text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)

    lines = text.splitlines()
    formatted = []
    in_list = False

    for line in lines:
        line = line.strip()

        if line.startswith(("•", "-", "*")):
            if not in_list:
                formatted.append("<ul>")
                in_list = True
            formatted.append(f"<li>{line[1:].strip()}</li>")
        else:
            if in_list:
                formatted.append("</ul>")
                in_list = False
            if line:
                formatted.append(f"<p>{line}</p>")

    if in_list:
        formatted.append("</ul")

    return "".join(formatted)


# ==========================================================
# JOB EMAIL TEMPLATE
# ==========================================================
def build_job_email_html(job: dict):
    role = job.get("job_title", "")
    description = job.get("job_description", "")
    job_id = job.get("jobid", "")

    apply_url = f"https://www.hiringcircle.us/jobs/{job_id}"

    return f"""
    <html>
    <body>
        <h2>{role}</h2>
        <p>{description}</p>
        <a href="{apply_url}">Apply</a>
    </body>
    </html>
    """


# ==========================================================
# SEND JOB EMAIL
# ==========================================================
def send_job_notification(job: dict):
    recipients = [EMAIL_TO] if EMAIL_TO else []

    if not recipients:
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"New Job Opening: {job.get('job_title','')}"
    msg["From"] = EMAIL_USER
    msg["To"] = ", ".join(recipients)

    html = build_job_email_html(job)
    msg.attach(MIMEText(html, "html"))

    return send_email_with_retry(msg, recipients)


# ==========================================================
# ATTACH FILE
# ==========================================================
def attach_file(msg, file_path):
    if not file_path:
        return

    try:
        with open(file_path, "rb") as f:
            file_data = f.read()
            mime_type, _ = mimetypes.guess_type(file_path)

            if mime_type:
                maintype, subtype = mime_type.split("/")
            else:
                maintype, subtype = "application", "octet-stream"

            part = MIMEBase(maintype, subtype)
            part.set_payload(file_data)
            encoders.encode_base64(part)

            filename = os.path.basename(file_path)
            part.add_header("Content-Disposition", f'attachment; filename="{filename}"')

            msg.attach(part)

    except Exception as e:
        logger.warning(f"Attach failed: {file_path} → {e}")


# ==========================================================
# SHORTLIST EMAIL HTML
# ==========================================================
def build_shortlist_email_html(job_title: str, candidates: List[Tuple]):
    candidates_html = ""

    for score, _, _, report_path, name, _ in candidates:
        color = "#22c55e" if score >= 90 else "#f59e0b" if score >= 75 else "#ef4444"

        candidates_html += f"""
        <tr>
            <td style="padding:12px;">{name or 'Unknown'}</td>
            <td style="padding:12px;text-align:center;">
                <span style="background:{color};color:white;padding:4px 12px;border-radius:12px;">
                    {score:.1f}%
                </span>
            </td>
            <td style="padding:12px;text-align:center;">
                <a href="https://www.hiringcircle.us/uploads/{report_path}">View Report</a>
            </td>
        </tr>
        """

    return f"""
    <html>
    <body style="font-family:Arial;padding:20px;">
        <h2>Top Matches - {job_title}</h2>
        <table width="100%" border="1" cellspacing="0">
            <tr>
                <th>Candidate</th>
                <th>Score</th>
                <th>Report</th>
            </tr>
            {candidates_html}
        </table>
    </body>
    </html>
    """


# ==========================================================
# SEND SHORTLIST EMAIL
# ==========================================================
def send_shortlist_email(recipient: str, job_title: str, candidates: List[Tuple]):

    if not recipient or not candidates:
        return False

    msg = MIMEMultipart("mixed")

    msg["Subject"] = f"Top Candidate Matches for: {job_title}"
    msg["From"] = EMAIL_USER
    msg["To"] = recipient

    html = build_shortlist_email_html(job_title, candidates)
    msg.attach(MIMEText(html, "html"))

    attached = set()

    for _, _, resume_path, report_path, _, _ in candidates:

        if report_path and report_path not in attached:
            attach_file(msg, report_path)
            attached.add(report_path)

        if resume_path and resume_path not in attached:
            attach_file(msg, resume_path)
            attached.add(resume_path)

    logger.info(f"Sending shortlist email with {len(attached)} attachments")

    return send_email_with_retry(msg, [recipient])
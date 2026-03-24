"""
Email Service for Hiring Circle Platform (FINAL VERSION)
"""

import os
import smtplib
import logging
import time
import mimetypes
import re
from typing import List, Tuple

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

logger = logging.getLogger("email_service")

# ==========================================================
# CONFIG
# ==========================================================
EMAIL_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("SMTP_PORT", 587))

EMAIL_USER = os.getenv("SMTP_USER", "")
EMAIL_PASS = os.getenv("SMTP_PASSWORD", "")

EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "HiringCircle")

SMTP_TIMEOUT = int(os.getenv("SMTP_TIMEOUT", 20))
SMTP_RETRIES = int(os.getenv("SMTP_RETRIES", 3))

# ==========================================================
# GET JOB RECIPIENTS (ENV)
# ==========================================================
def get_job_recipients():
    raw = os.getenv("JOB_ALERT_EMAILS", "")
    return [e.strip() for e in raw.split(",") if e.strip()]

# ==========================================================
# SEND EMAIL CORE
# ==========================================================
def send_email(msg, recipients):
    if not EMAIL_USER or not EMAIL_PASS:
        logger.warning("❌ Email credentials not configured")
        return False

    for attempt in range(SMTP_RETRIES):
        try:
            server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=SMTP_TIMEOUT)
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)

            server.sendmail(EMAIL_USER, recipients, msg.as_string())
            server.quit()

            logger.info("✅ Email sent successfully")
            return True

        except Exception as e:
            logger.warning(f"⚠️ Email attempt {attempt+1} failed: {e}")
            time.sleep(2)

    logger.error("❌ All email attempts failed")
    return False

# ==========================================================
# FORMAT JOB DESCRIPTION (RE-ADDED CLEAN VERSION)
# ==========================================================
def format_job_description_html(text: str) -> str:
    if not text:
        return ""

    # Bold (**text** → <strong>)
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
        formatted.append("</ul>")

    return "".join(formatted)

# ==========================================================
# JOB EMAIL TEMPLATE
# ==========================================================
def build_job_email_html(job: dict):
    role = job.get("job_title", "")
    description = job.get("job_description", "")
    job_id = job.get("jobid", "")

    formatted_desc = format_job_description_html(description)

    apply_url = f"https://www.hiringcircle.us/jobs/{job_id}"

    return f"""
    <html>
    <body>
        <h2>{role}</h2>
        {formatted_desc}
        <br/>
        <a href="{apply_url}">Apply Now</a>
    </body>
    </html>
    """

# ==========================================================
# SEND JOB EMAIL (BCC FIX)
# ==========================================================
def send_job_notification(job: dict):
    recipients = get_job_recipients()

    if not recipients:
        logger.warning("⚠️ No recipients configured (JOB_ALERT_EMAILS)")
        return False

    msg = MIMEMultipart("alternative")

    msg["Subject"] = f"New Job Opening: {job.get('job_title','')}"
    msg["From"] = EMAIL_USER
    msg["To"] = "no-reply@hiringcircle.us"

    html = build_job_email_html(job)
    msg.attach(MIMEText(html, "html"))

    # Include BCC recipients in send list
    all_recipients = ["no-reply@hiringcircle.us"] + recipients

    logger.info(f"📧 Sending job email to {len(recipients)} recipients")

    return send_email(msg, all_recipients)

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
            part.add_header("Content-Disposition", f'attachment; filename=\"{filename}\"')

            msg.attach(part)

    except Exception as e:
        logger.warning(f"⚠️ Attach failed: {file_path} → {e}")

# ==========================================================
# SHORTLIST EMAIL TEMPLATE
# ==========================================================
def build_shortlist_email_html(job_title: str, candidates: List[Tuple]):
    rows = ""

    for score, _, _, report_path, name, _ in candidates:
        rows += f"""
        <tr>
            <td>{name}</td>
            <td>{score:.1f}%</td>
            <td><a href="https://www.hiringcircle.us/uploads/{report_path}">View</a></td>
        </tr>
        """

    return f"""
    <html>
    <body>
        <h2>Top Candidates - {job_title}</h2>
        <table border="1">
            {rows}
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

    msg["Subject"] = f"Top Matches: {job_title}"
    msg["From"] = EMAIL_USER
    msg["To"] = recipient

    html = build_shortlist_email_html(job_title, candidates)
    msg.attach(MIMEText(html, "html"))

    for _, _, resume_path, report_path, _, _ in candidates:
        attach_file(msg, resume_path)
        attach_file(msg, report_path)

    return send_email(msg, [recipient])
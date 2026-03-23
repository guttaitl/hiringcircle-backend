import os
import smtplib
import logging
import time
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ==========================================================
# LOAD ENV
# ==========================================================
ROOT_ENV = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ROOT_ENV, override=True)


def require_env(value: Optional[str], name: str) -> str:
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


# ==========================================================
# CONFIG
# ==========================================================
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))

EMAIL_USER = require_env(os.getenv("EMAIL_USER"), "EMAIL_USER")
EMAIL_PASS = require_env(os.getenv("EMAIL_PASS"), "EMAIL_PASS")

EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "HiringCircle")

EMAIL_TO = os.getenv("EMAIL_TO", "")
EMAIL_BCC = os.getenv("EMAIL_BCC", "")

SMTP_TIMEOUT = int(os.getenv("SMTP_TIMEOUT", 20))
SMTP_RETRIES = int(os.getenv("SMTP_RETRIES", 3))

logger = logging.getLogger("email_service")

# ==========================================================
# CONNECTION POOL (REUSE SMTP CONNECTION)
# ==========================================================
def send_email_with_retry(msg, recipients):

    for attempt in range(SMTP_RETRIES):

        try:
            server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=SMTP_TIMEOUT)
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)

            server.sendmail(
                EMAIL_USER,
                recipients,
                msg.as_string()
            )

            server.quit()

            logger.info("Email sent successfully")
            return True

        except Exception as e:
            logger.warning(
                f"Email attempt {attempt+1}/{SMTP_RETRIES} failed: {e}"
            )
            time.sleep(2)

    logger.error("All email attempts failed")
    return False

# ==========================================================
# JOB DESCRIPTION FORMATTER
# ==========================================================
import re


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
        formatted.append("</ul>")

    return "".join(formatted)


# ==========================================================
# JOB EMAIL HTML TEMPLATE
# ==========================================================
def build_job_email_html(job: dict):

    role = job.get("job_title", "")
    company = job.get("poster_company", "Company")
    location = job.get("location", "-")
    description = job.get("job_description", "")
    skills = job.get("skills", "")
    responsibilities = job.get("responsibilities", "")
    job_id = job.get("jobid", "")

    apply_url = f"https://www.hiringcircle.us/jobs/{job_id}"

    skills_html = "".join(
        f"<li style='margin-bottom:6px'>{s.strip()}</li>"
        for s in skills.split("\n") if s.strip()
    )

    resp_html = "".join(
        f"<li style='margin-bottom:6px'>{r.strip()}</li>"
        for r in responsibilities.split("\n") if r.strip()
    )

    return f"""
<html>
<body style="font-family:Arial;background:#f3f4f6;padding:30px;">

<table width="720" align="center" cellpadding="0" cellspacing="0" style="background:#ffffff;border:1px solid #ddd;">

<tr>
<td style="background:#4f46e5;color:#ffffff;padding:16px;font-size:20px;font-weight:700;">
<table width="100%">
<tr>
<td>{company}</td>
<td align="right">
<a href="{apply_url}"
style="background:#22c55e;color:#ffffff;padding:10px 18px;text-decoration:none;border-radius:4px;font-weight:bold;">
Apply
</a>
</td>
</tr>
</table>
</td>
</tr>

<tr>
<td style="padding:28px">

<p style="margin:0 0 10px 0;font-size:16px;">
<strong>Role:</strong> {role}
</p>

<p style="margin:0 0 20px 0;font-size:16px;">
<strong>Location:</strong> {location}
</p>

<h3 style="margin-bottom:8px;">Description</h3>
<p style="line-height:1.6;color:#333;">
{description}
</p>

<h3 style="margin-top:24px;margin-bottom:8px;">Skills</h3>
<ul style="padding-left:20px;color:#333;">
{skills_html}
</ul>

<h3 style="margin-top:24px;margin-bottom:8px;">Responsibilities</h3>
<ul style="padding-left:20px;color:#333;">
{resp_html}
</ul>

</td>
</tr>

</table>

</body>
</html>
"""

# ==========================================================
# SEND JOB NOTIFICATION
# ==========================================================
def send_job_notification(job: dict):

    to_recipients = [e.strip() for e in EMAIL_TO.split(",") if e.strip()]
    bcc_recipients = [e.strip() for e in EMAIL_BCC.split(",") if e.strip()]

    recipients = to_recipients + bcc_recipients

    if not recipients:
        logger.warning("No job notification recipients configured")
        return False

    subject = f"New Job Opening: {job.get('job_title','')}"

    html = build_job_email_html(job)

    msg = MIMEMultipart("alternative")

    msg["Subject"] = subject
    msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_USER}>"
    msg["To"] = ", ".join(to_recipients)

    if bcc_recipients:
        msg["Bcc"] = ", ".join(bcc_recipients)

    msg.attach(MIMEText(html, "html"))

    logger.info("Sending job notification email")

    return send_email_with_retry(msg, recipients)


# ==========================================================
# VERIFICATION EMAIL
# ==========================================================
def send_verification_email(recipient: str, verification_url: str):

    if not recipient:
        return False

    subject = "Verify your HiringCircle account"

    html = f"""
    <html>
    <body>
    <h2>Welcome to HiringCircle</h2>

    <p>Please verify your email:</p>

    <p>
    <a href="{verification_url}"
    style="background:#2563eb;color:#fff;padding:10px 18px;text-decoration:none;">
    Verify Email
    </a>
    </p>

    <p>{verification_url}</p>

    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")

    msg["Subject"] = subject
    msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_USER}>"
    msg["To"] = recipient

    msg.attach(MIMEText(html, "html"))

    return send_email_with_retry(msg, [recipient])
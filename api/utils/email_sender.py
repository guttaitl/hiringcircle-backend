# ==========================================================
# EMAIL SENDER (RAILWAY SAFE + PRODUCTION READY)
# ==========================================================

import os
import smtplib
import logging
import time
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional
import re

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ==========================================================
# LOAD ENV (ONLY LOCAL)
# ==========================================================

ROOT_ENV = Path(__file__).resolve().parent.parent / ".env.development"

if os.getenv("RAILWAY_ENVIRONMENT") is None:
    load_dotenv(ROOT_ENV)

logger = logging.getLogger("email_service")

# ==========================================================
# CONFIG LOADER (NO CRASHES)
# ==========================================================

def get_email_config():
    return {
        "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("SMTP_PORT", 587)),
        "user": os.getenv("SMTP_USER"),
        "password": os.getenv("SMTP_PASSWORD"),
        "from_name": os.getenv("EMAIL_FROM_NAME", "HiringCircle"),
        "from_email": os.getenv("SMTP_FROM") or os.getenv("SMTP_USER"),
        "to": os.getenv("DEFAULT_TO_EMAIL", ""),
        "bcc": os.getenv("DEFAULT_BCC_EMAIL", ""),
        "timeout": int(os.getenv("SMTP_TIMEOUT", 20)),
        "retries": int(os.getenv("SMTP_RETRIES", 3)),
    }

# ==========================================================
# SEND EMAIL WITH RETRY (SAFE)
# ==========================================================

def send_email_with_retry(msg, recipients):

    config = get_email_config()

    if not config["user"] or not config["password"]:
        logger.warning("⚠️ SMTP not configured, skipping email")
        return False

    for attempt in range(config["retries"]):
        try:
            server = smtplib.SMTP(
                config["host"],
                config["port"],
                timeout=config["timeout"]
            )

            server.starttls()
            server.login(config["user"], config["password"])

            server.sendmail(
                config["from_email"],
                recipients,
                msg.as_string()
            )

            server.quit()

            logger.info("✅ Email sent successfully")
            return True

        except Exception as e:
            logger.warning(
                f"⚠️ Email attempt {attempt+1}/{config['retries']} failed: {e}"
            )
            time.sleep(2)

    logger.error("❌ All email attempts failed")
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
        formatted.append("</ul>")

    return "".join(formatted)

# ==========================================================
# BUILD JOB EMAIL HTML
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

<p><strong>Role:</strong> {role}</p>
<p><strong>Location:</strong> {location}</p>

<h3>Description</h3>
<p>{description}</p>

<h3>Skills</h3>
<ul>{skills_html}</ul>

<h3>Responsibilities</h3>
<ul>{resp_html}</ul>

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

    config = get_email_config()

    to_recipients = [e.strip() for e in config["to"].split(",") if e.strip()]
    bcc_recipients = [e.strip() for e in config["bcc"].split(",") if e.strip()]

    all_recipients = to_recipients + bcc_recipients

    if not all_recipients:
        logger.warning("⚠️ No recipients configured")
        return False

    subject = f"New Job Opening: {job.get('job_title','')}"
    html = build_job_email_html(job)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{config['from_name']} <{config['from_email']}>"
    msg["To"] = ", ".join(to_recipients)

    msg.attach(MIMEText(html, "html"))

    logger.info(f"📤 Sending email to: {to_recipients}")
    if bcc_recipients:
        logger.info(f"📤 BCC: {bcc_recipients}")

    return send_email_with_retry(msg, all_recipients)

# ==========================================================
# SEND VERIFICATION EMAIL
# ==========================================================

def send_verification_email(recipient: str, verification_url: str):

    config = get_email_config()

    if not recipient:
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Verify your HiringCircle account"
    msg["From"] = f"{config['from_name']} <{config['from_email']}>"
    msg["To"] = recipient

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

    msg.attach(MIMEText(html, "html"))

    return send_email_with_retry(msg, [recipient])
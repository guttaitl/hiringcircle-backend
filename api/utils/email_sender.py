# ==========================================================
# EMAIL SENDER (LOCKED PRODUCTION VERSION)
# ==========================================================

import os
import base64
import logging
from pathlib import Path
from dotenv import load_dotenv

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from openai import OpenAI

# ==========================================================
# LOAD ENV (LOCAL ONLY)
# ==========================================================

ROOT_ENV = Path(__file__).resolve().parent.parent / ".env.development"

if os.getenv("RAILWAY_ENVIRONMENT") is None:
    load_dotenv(ROOT_ENV)

logger = logging.getLogger("email_service")

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

# ==========================================================
# CONFIG
# ==========================================================

def get_email_config():
    return {
        "bcc": os.getenv("JOB_ALERT_BCC", ""),
        "from_name": os.getenv("EMAIL_FROM_NAME", "HiringCircle"),
        "client_id": os.getenv("GMAIL_CLIENT_ID"),
        "client_secret": os.getenv("GMAIL_CLIENT_SECRET"),
        "refresh_token": os.getenv("GMAIL_REFRESH_TOKEN"),
    }


# ==========================================================
# SEND EMAIL (GMAIL API)
# ==========================================================

def send_email_gmail_api(to_list, bcc_list, subject, html):

    config = get_email_config()

    if not config["client_id"] or not config["refresh_token"]:
        logger.error("Gmail API not configured")
        return False

    try:
        creds = Credentials(
            None,
            refresh_token=config["refresh_token"],
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            token_uri="https://oauth2.googleapis.com/token"
        )

        service = build("gmail", "v1", credentials=creds)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{config['from_name']} <no-reply@hiringcircle.us>"
        msg["Reply-To"] = "no-reply@hiringcircle.us"
        msg["To"] = ", ".join(to_list or ["no-reply@hiringcircle.us"])

        if bcc_list:
            msg["Bcc"] = ", ".join(bcc_list)

        msg.attach(MIMEText(html, "html"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        service.users().messages().send(
            userId="me",
            body={"raw": raw}
        ).execute()

        logger.info(f"Email sent to {len(bcc_list)} users")
        return True

    except Exception as e:
        logger.error(f"Email failed: {e}")
        return False


# ==========================================================
# AI RESPONSIBILITIES (NO FALLBACK)
# ==========================================================

def generate_ai_responsibilities(role: str, skills: str, experience: str = ""):

    # ✅ ADD THIS HERE
    if not client:
        logger.error("OpenAI client not initialized (missing API key)")
        return None

    try:
        prompt = f"""
Generate 6 to 8 professional job responsibilities.

Role: {role}
Skills: {skills}
Experience: {experience}

Rules:
- Must be specific to role and skills
- Must include technologies/tools from skills
- Use strong action verbs (Design, Develop, Implement, Optimize)
- Avoid generic lines
- Each line must feel realistic for production jobs
- Output ONLY bullet points
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6
        )

        content = response.choices[0].message.content.strip()

        lines = [
            line.strip("•- ").strip()
            for line in content.split("\n")
            if line.strip()
        ]

        if len(lines) < 3:
            return None

        return lines[:7]

    except Exception as e:
        logger.error(f"AI responsibility generation failed: {e}")
        return None

def build_job_email_html(job: dict):

    role = job.get("job_title", "")
    company = job.get("user_company") or "HiringCircle"
    location = job.get("location", "-")
    job_type = job.get("employment_type", "Contract")
    interview = job.get("interview", "Inperson")
    description = job.get("job_description", "")
    skills = job.get("skills", "") or ""
    responsibilities = job.get("responsibilities") or ""

    apply_url = f"https://www.hiringcircle.us/apply/{job.get('jobid')}"

    skills_list = [s.strip() for s in skills.split("\n") if s.strip()]
    resp_list = [r.strip() for r in responsibilities.split("\n") if r.strip()]

    import re

    desc = (description or "").strip()

    # Normalize multiple spaces
    desc = re.sub(r"\s+", " ", desc)

    # Replace variations of "we are"
    desc = re.sub(
        r"^(we\s+are|we're)\b",
        f"{company} is",
        desc,
        flags=re.IGNORECASE
    )

    # If still doesn't start with company → enforce recruiter tone
    if not desc.lower().startswith(company.lower()):
        if desc:
            desc = f"{company} is seeking {desc[0].lower() + desc[1:]}"
        else:
            desc = f"{company} is seeking a qualified candidate for this role."

    description = desc
    skills_html = "".join(f"<li>{s}</li>" for s in skills_list)
    resp_html = "".join(f"<li>{r}</li>" for r in resp_list)

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
    body {{
        margin:0;
        padding:0;
        background:#ffffff;
        font-family: Calibri, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
        color:#222;
        line-height:1.5;
    }}

    .wrap {{
        padding:0 6px;
    }}

    .text {{
        font-size:14px;
    }}

    table {{
        border-collapse:collapse;
        font-size:14px;
    }}

    td {{
        padding:2px 8px 2px 0;
        vertical-align:top;
    }}

    .label {{
        font-weight:600;
        white-space:nowrap;
    }}

    ul {{
        margin:6px 0 10px 18px;
        padding:0;
    }}

    li {{
        margin:2px 0;
    }}

    /* MOBILE */
    @media only screen and (max-width:600px) {{
        .wrap {{
            padding:0 6px !important;
        }}

        td {{
            display:block;
            width:100%;
            padding:2px 0 !important;
        }}

        .label {{
            margin-top:6px;
        }}
    }}
</style>
</head>

<body>
<div class="wrap text">

    <!-- APPLY LINK (natural style) -->
    <p style="margin:6px 0 10px 0;">
        <a href="{apply_url}" style="color:#0b57d0; text-decoration:underline;">
            Apply here
        </a>
    </p>

    <!-- JOB DETAILS -->
    <table>
        <tr>
            <td class="label">Role:</td>
            <td>{role}</td>
        </tr>
        <tr>
            <td class="label">Location:</td>
            <td>{location}</td>
        </tr>
        <tr>
            <td class="label">Type:</td>
            <td>{job_type}</td>
        </tr>
        <tr>
            <td class="label">Interview:</td>
            <td>{interview}</td>
        </tr>
        </table>

        <table width="100%">
        <tr><td height="10"></td></tr>
        </table>


        <table width="100%">
        <tr>
        <td style="padding:0 12px;">
            <p style="margin:0;">
                {description}
            </p>
        </td>
        </tr>
        </table>

        <table width="100%">
        <tr><td height="10"></td></tr>
        </table>

    <!-- SKILLS -->
    <p style="margin:10px 0 4px 0; font-weight:600;">Skills:</p>
    <ul>
        {skills_html}
    </ul>
"""

    if resp_list:
        html += f"""
    <!-- RESPONSIBILITIES -->
    <p style="margin:10px 0 4px 0; font-weight:600;">Responsibilities:</p>
    <ul>
        {resp_html}
    </ul>
"""

    # ✅ ADD GAP (email-safe)
    html += """
    <table width="100%">
        <tr><td height="14"></td></tr>
    </table>
    """

    # ✅ ADD SIGNATURE
    poster_name = job.get("user_name") or ""

    html += f"""
    <!-- SIGNATURE -->
    <p style="margin:0;">
        {poster_name}<br>
        {company}
    </p>
"""

    html += """
</div>
</body>
</html>
"""
    return html
# ==========================================================
# SEND JOB EMAIL
# ==========================================================
def send_job_notification(job: dict):

    config = get_email_config()

    bcc_raw = config.get("bcc", "") or ""
    bcc_list = [e.strip() for e in bcc_raw.split(",") if e.strip()]

    if not bcc_list:
        logger.warning("No recipients configured")
        return False

    subject = f"New Job Opening: {job.get('job_title', '')}"
    html = build_job_email_html(job)

    return send_email_gmail_api(
        [],
        bcc_list,
        subject,
        html
    )

# ==========================================================
# VERIFY EMAIL
# ==========================================================

def send_verification_email(recipient: str, verification_url: str):

    if not recipient:
        return False

    html = f"""
    <html>
    <body style="font-family:Arial;">
        <h2>Welcome to HiringCircle</h2>
        <p>Please verify your email:</p>
        <a href="{verification_url}">Verify Email</a>
    </body>
    </html>
    """

    return send_email_gmail_api(
        [recipient],
        [],
        "Verify your account",
        html
    )
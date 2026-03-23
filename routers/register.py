from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
import secrets
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import psycopg2
from passlib.hash import bcrypt

router = APIRouter()

# ==========================================================
# ENV VARIABLES
# ==========================================================

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://www.hiringcircle.us")

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM")

DATABASE_URL = os.getenv("DATABASE_URL")

# ==========================================================
# REQUEST MODEL
# ==========================================================

class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    contact: str
    company: str
    role: str
    password: str

# ==========================================================
# EMAIL FUNCTION
# ==========================================================

def send_verification_email(email: str, token: str):

    # 🔍 DEBUG (VERY IMPORTANT)
    print("DEBUG SMTP_HOST:", repr(SMTP_HOST))
    print("DEBUG SMTP_USER:", repr(SMTP_USER))
    print("DEBUG SMTP_PASSWORD:", "SET" if SMTP_PASSWORD else None)

    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        print("❌ EMAIL CONFIG MISSING")
        return

    verify_link = f"https://hiringcircle-api.up.railway.app/api/verify?token={token}"

    subject = "Verify your email - HiringCircle"

    html = f"""
    <h2>Welcome to HiringCircle</h2>

    <p>Please verify your email to activate your account.</p>

    <p>
        <a href="{verify_link}" style="background:#4F46E5;color:white;padding:10px 20px;text-decoration:none;border-radius:5px;">
            Verify Email
        </a>
    </p>

    <p>If button doesn't work, copy this link:</p>
    <p>{verify_link}</p>

    <p>If you didn't create this account, ignore this email.</p>
    """

    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_FROM or SMTP_USER
        msg["To"] = email
        msg["Subject"] = subject

        msg.attach(MIMEText(html, "html"))

        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, email, msg.as_string())
        server.quit()

        print("✅ Email sent successfully to", email)

    except Exception as e:
        print("❌ EMAIL ERROR:", str(e))


# ==========================================================
# REGISTER API
# ==========================================================

@router.post("/register")
async def register_user(data: RegisterRequest):

    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="Database not configured")

    token = secrets.token_urlsafe(32)
    password_hash = bcrypt.hash(data.password)

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # 🔍 Check if user already exists
        cur.execute("SELECT id FROM usersdata WHERE email=%s", (data.email,))
        existing = cur.fetchone()

        if existing:
            raise HTTPException(status_code=400, detail="User already registered")

        # ✅ Insert new user
        cur.execute(
            """
            INSERT INTO usersdata
            (full_name,email,contact,company,role,password_hash,verified,verification_token)
            VALUES (%s,%s,%s,%s,%s,%s,false,%s)
            """,
            (
                data.full_name,
                data.email,
                data.contact,
                data.company,
                data.role,
                password_hash,
                token
            )
        )

        conn.commit()
        print("✅ User inserted successfully")

    except HTTPException:
        raise

    except Exception as e:
        print("❌ DATABASE ERROR:", str(e))
        raise HTTPException(status_code=500, detail="User registration failed")

    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

    # 📧 Send verification email
    send_verification_email(data.email, token)

    return {
        "status": "success",
        "message": "Verification email sent. Please check your email."
    }
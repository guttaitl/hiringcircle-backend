from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import os
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from api.db import get_db
from api.utils.security import verify_password, create_access_token, hash_password
from api.schemas.auth_schema import LoginRequest, EmailCheckRequest

router = APIRouter()

# ==========================================================
# EMAIL CONFIGURATION
# ==========================================================
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://hiringcircle.us")
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "HiringCircle")

# ==========================================================
# EMAIL FUNCTION
# ==========================================================
def send_verification_email(email: str, token: str):
    """Send verification email to user"""
    if not all([EMAIL_HOST, EMAIL_USER, EMAIL_PASS]):
        print("EMAIL ERROR: Email configuration missing")
        return False

    verify_link = f"{FRONTEND_URL}/verify?token={token}"

    subject = "Verify your email - HiringCircle"

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #2563eb;">Welcome to HiringCircle!</h2>
            
            <p>Thank you for registering. Please verify your email to activate your account.</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{verify_link}" 
                   style="background-color: #2563eb; color: white; padding: 12px 30px; 
                          text-decoration: none; border-radius: 6px; display: inline-block;">
                    Verify My Email
                </a>
            </div>
            
            <p>Or copy and paste this link in your browser:</p>
            <p style="word-break: break-all; color: #666;">{verify_link}</p>
            
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            
            <p style="font-size: 12px; color: #999;">
                If you didn't create this account, you can safely ignore this email.
            </p>
        </div>
    </body>
    </html>
    """

    msg = MIMEMultipart()
    msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_USER}>"
    msg["To"] = email
    msg["Subject"] = subject
    msg.attach(MIMEText(html, "html"))

    try:
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, email, msg.as_string())
        server.quit()
        print(f"✅ Verification email sent to: {email}")
        return True
    except Exception as e:
        print(f"EMAIL ERROR: {e}")
        return False

# ==========================================================
# LOGIN
# ==========================================================
@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):

    result = db.execute(
        text("""
        SELECT password_hash, verified, role
        FROM usersdata
        WHERE email = :email
        """),
        {"email": payload.email}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    password_hash = result[0]
    verified = result[1]
    role = result[2]

    # verify password
    if not verify_password(payload.password, password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # verify email
    if not verified:
        raise HTTPException(status_code=401, detail="Email not verified")

    role = (role or "").strip().lower()

    if role in ["employer", "employer login"]:
        role = "EMPLOYER"
    else:
        role = "USER"

    # create JWT
    token = create_access_token({
        "email": payload.email,
        "role": role
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": role
    }

# ==========================================================
# REGISTER EMAIL CHECK
# ==========================================================
@router.post("/register/check")
def check_email(payload: EmailCheckRequest, db: Session = Depends(get_db)):

    query = text("""
        SELECT email
        FROM usersdata
        WHERE LOWER(email) = LOWER(:email)
    """)

    user = db.execute(query, {"email": payload.email}).fetchone()

    if user:
        return {"status": "EXISTS_VERIFIED"}

    return {"status": "AVAILABLE"}

# ==========================================================
# REGISTER
# ==========================================================
@router.post("/register")
def register(payload: dict, db: Session = Depends(get_db)):

    # check if email already exists
    existing = db.execute(
        text("""
        SELECT email
        FROM usersdata
        WHERE email = :email
        """),
        {"email": payload["email"]}
    ).fetchone()

    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    token = secrets.token_urlsafe(32)
    password_hash = hash_password(payload["password"])

    try:
        db.execute(
            text("""
            INSERT INTO usersdata
            (
                full_name,
                email,
                contact,
                company,
                role,
                password_hash,
                verified,
                verification_token,
                created_date
            )
            VALUES
            (
                :full_name,
                :email,
                :contact,
                :company,
                :role,
                :password_hash,
                false,
                :token,
                NOW()
            )
            """),
            {
                "full_name": payload["full_name"],
                "email": payload["email"],
                "contact": payload["contact"],
                "company": payload.get("company", ""),
                "role": payload["role"],
                "password_hash": password_hash,
                "token": token
            }
        )

        db.commit()

        # Send verification email
        email_sent = send_verification_email(payload["email"], token)
        
        if not email_sent:
            print(f"Warning: Failed to send verification email to {payload['email']}")

        return {
            "status": "success",
            "message": "Verification email sent. Please check your email."
        }
        
    except Exception as e:
        db.rollback()
        print(f"REGISTRATION ERROR: {e}")
        raise HTTPException(status_code=500, detail="Registration failed. Please try again.")

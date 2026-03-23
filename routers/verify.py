from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
import psycopg2
import os

router = APIRouter()

DATABASE_URL = os.getenv("DATABASE_URL")
FRONTEND_LOGIN_URL = os.getenv("FRONTEND_URL", "https://www.hiringcircle.us")

@router.get("/verify")
def verify_email(token: str):

    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="Database not configured")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # 🔍 Check token
        cur.execute(
            """
            SELECT id FROM usersdata
            WHERE verification_token = %s
            """,
            (token,)
        )

        user = cur.fetchone()

        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired verification link")

        # ✅ Update user
        cur.execute(
            """
            UPDATE usersdata
            SET verified = true,
                verification_token = NULL
            WHERE verification_token = %s
            """,
            (token,)
        )

        conn.commit()

    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

    # 🚀 Redirect to frontend login page after verification
    return RedirectResponse(
        url=f"{FRONTEND_LOGIN_URL}/login?verified=true",
        status_code=302
    )
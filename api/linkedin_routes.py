from fastapi import APIRouter
import requests
import os

router = APIRouter()

@router.get("/linkedin/callback")
def linkedin_callback(code: str):
    res = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": os.getenv("LINKEDIN_REDIRECT_URI"),
            "client_id": os.getenv("LINKEDIN_CLIENT_ID"),
            "client_secret": os.getenv("LINKEDIN_CLIENT_SECRET"),
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    return res.json()
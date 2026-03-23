import smtplib
from email.mime.text import MIMEText
import os
import time

SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


def send_email_safe(to_list, subject, html):
    msg = MIMEText(html, "html")
    msg["Subject"] = subject
    msg["From"] = SMTP_EMAIL
    msg["To"] = ", ".join(to_list)

    for _ in range(3):  # retry 3 times
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(SMTP_EMAIL, SMTP_PASSWORD)
                server.sendmail(SMTP_EMAIL, to_list, msg.as_string())
            return True
        except Exception:
            time.sleep(3)

    return False

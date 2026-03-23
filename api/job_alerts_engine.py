from typing import Dict, List
from db import get_db_conn


def job_matches_alert(job: Dict, alert: Dict) -> bool:
    # Keyword match
    alert_keywords = alert["keywords"].lower().split()
    job_text = f"{job.get('title','')} {job.get('skills','')}".lower()

    keyword_match = all(k in job_text for k in alert_keywords)

    # Location match (optional)
    location_match = True
    if alert.get("location"):
        location_match = alert["location"].lower() in (job.get("location") or "").lower()

    # Job type match (optional)
    job_type_match = True
    if alert.get("job_type"):
        job_type_match = alert["job_type"].lower() == (job.get("job_type") or "").lower()

    return keyword_match and location_match and job_type_match


def trigger_job_alerts(job: Dict):
    print("🔔 trigger_job_alerts CALLED", flush=True)

    conn = get_db_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, user_email, keywords, location, job_type
        FROM job_alerts
    """)
    alerts = cur.fetchall()

    print(f"🔎 Found {len(alerts)} alerts")

    for a in alerts:
        alert = {
            "id": a[0],
            "user_email": a[1],
            "keywords": a[2],
            "location": a[3],
            "job_type": a[4],
        }

        print("Checking alert:", alert)

        if job_matches_alert(job, alert):
            print("✅ MATCHED → sending email")
            send_job_alert(alert["user_email"], job)
        else:
            print("❌ Not matched")

    cur.close()
    conn.close()

def send_job_alert(email: str, job: Dict):
    # 🔔 For now just log / print
    print(f"📢 Job Alert → {email}: {job['title']} ({job['location']})")

    # Later:
    # - Email
    # - Push notification
    # - In-app alert

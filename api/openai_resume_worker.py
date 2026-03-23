import os
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

from openai import OpenAI

# =========================
# CONFIG
# =========================

BATCH_SIZE = 5
SLEEP_SECONDS = 5
PARSER_VERSION = "openai_html_v1"

OPENAI_MODEL = "gpt-4.1-mini"  # or your preferred model

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in environment")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# =========================
# OPENAI CALL
# =========================

def generate_html(resume_text: str) -> str:
    prompt = f"""
You are an ATS resume formatter.

Convert the resume text below into STRICT, CLEAN, READABLE HTML.

MANDATORY RULES:
- Use semantic HTML ONLY
- Use <h2> for section headings
- Use <ul><li> for bullet points
- Use <p> for paragraphs
- Preserve line breaks and structure
- DO NOT output plain text
- DO NOT collapse everything into one paragraph
- DO NOT add explanations or comments
- DO NOT hallucinate content

SECTIONS TO IDENTIFY (if present):
- Summary
- Skills
- Experience
- Education
- Certifications
- Projects

OUTPUT FORMAT EXAMPLE (you MUST follow this style):

<h2>Summary</h2>
<p>Short professional summary here.</p>

<h2>Skills</h2>
<ul>
  <li>Java</li>
  <li>Spring Boot</li>
  <li>AWS</li>
</ul>

<h2>Experience</h2>
<ul>
  <li>
    <strong>Company Name</strong> – Role<br/>
    <em>Jan 2020 – Present</em>
    <ul>
      <li>Responsibility 1</li>
      <li>Responsibility 2</li>
    </ul>
  </li>
</ul>

NOW FORMAT THIS RESUME TEXT:

{resume_text}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You generate clean, structured HTML resumes."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )

    return response.choices[0].message.content.strip()

# =========================
# DB HELPERS
# =========================

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def fetch_pending_resumes(conn):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id, resume_text
            FROM candidate_resumes
            WHERE
                formatted_html IS NULL
                AND (parser_version IS NULL OR parser_version = 'pending')
                AND is_deleted = false
            ORDER BY created_at
            LIMIT %s
            FOR UPDATE SKIP LOCKED
        """, (BATCH_SIZE,))
        return cur.fetchall()

def mark_success(conn, resume_id, html):
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE candidate_resumes
            SET
                formatted_html = %s,
                parser_version = %s,
                parsed_successfully = true,
                last_parsed_at = NOW(),
                updated_at = NOW()
            WHERE id = %s
        """, (html, PARSER_VERSION, resume_id))
    conn.commit()

def mark_failed(conn, resume_id, error_msg):
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE candidate_resumes
            SET
                parser_version = 'failed',
                parsed_successfully = false,
                last_parsed_at = NOW(),
                updated_at = NOW()
            WHERE id = %s
        """, (resume_id,))
    conn.commit()

# =========================
# MAIN LOOP
# =========================

def run_worker():
    print("🟢 OpenAI Resume Worker started")

    while True:
        conn = get_connection()

        try:
            resumes = fetch_pending_resumes(conn)

            if not resumes:
                print("⏸ No pending resumes. Sleeping...")
                time.sleep(SLEEP_SECONDS)
                continue

            print(f"🔄 Processing batch of {len(resumes)} resumes")

            for r in resumes:
                resume_id = r["id"]
                text = r["resume_text"]

                print(f"➡️ Processing resume {resume_id}")

                try:
                    html = generate_html(text)
                    mark_success(conn, resume_id, html)
                    print(f"✅ Success {resume_id}")

                except Exception as e:
                    print(f"❌ Failed {resume_id}: {e}")
                    mark_failed(conn, resume_id, str(e))

        finally:
            conn.close()

        time.sleep(SLEEP_SECONDS)

if __name__ == "__main__":
    run_worker()

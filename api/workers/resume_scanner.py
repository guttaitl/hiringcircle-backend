import os
import time
import logging

from api.db import get_db_conn

UPLOAD_DIR = "/app/uploads"   # ⚠️ Docker path
SCAN_INTERVAL = 20

logger = logging.getLogger("resume_scanner")


# -----------------------------
# HASH FUNCTION
# -----------------------------
def get_file_hash(file_path):
    import hashlib

    hasher = hashlib.md5()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)

    return hasher.hexdigest()


# -----------------------------
# INSERT INTO DB
# -----------------------------
def insert_resume_if_new(file_path):
    conn = get_db_conn()
    cur = conn.cursor()

    try:
        file_hash = get_file_hash(file_path)

        # Check if already exists
        cur.execute("""
            SELECT id FROM candidate_resumes
            WHERE file_hash = %s
        """, (file_hash,))

        if cur.fetchone():
            return False

        # Insert new resume
        cur.execute("""
            INSERT INTO candidate_resumes (
                file_path,
                file_hash,
                parsed_successfully
            )
            VALUES (%s, %s, false)
        """, (
            file_path,
            file_hash
        ))

        conn.commit()
        return True

    except Exception as e:
        logger.error(f"❌ Insert failed: {e}")
        conn.rollback()
        return False

    finally:
        cur.close()
        conn.close()


# -----------------------------
# SCAN LOOP (THIS IS STEP 3)
# -----------------------------
def scan_uploads():
    try:
        files = os.listdir(UPLOAD_DIR)

        for file in files:
            file_path = os.path.join(UPLOAD_DIR, file)

            if not os.path.isfile(file_path):
                continue

            inserted = insert_resume_if_new(file_path)

            if inserted:
                logger.info(f"📄 New resume added: {file}")

    except Exception as e:
        logger.error(f"❌ Scan error: {e}")


# -----------------------------
# START BACKGROUND LOOP
# -----------------------------
def start_scanner():
    logger.info("🚀 Resume scanner started...")

    while True:
        scan_uploads()
        time.sleep(SCAN_INTERVAL)
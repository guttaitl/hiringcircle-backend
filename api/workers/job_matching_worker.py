import logging
import os
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from api.db import get_db_conn
from api.ai.perfect_match_engine import process_job_matching

logger = logging.getLogger("job_matching_worker")

MAX_MATCH_WORKERS = 3
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 60
POLL_INTERVAL = 2
LOCK_TIMEOUT_MINUTES = 10

WORKER_ID = f"{socket.gethostname()}-{os.getpid()}"


# ==========================================================
# RECOVER STUCK JOBS
# ==========================================================

def recover_stuck_jobs():
    conn = get_db_conn()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE job_matching_queue
            SET status='PENDING',
                locked_at=NULL,
                locked_by=NULL
            WHERE status='PROCESSING'
            AND locked_at < NOW() - INTERVAL %s
        """, (f'{LOCK_TIMEOUT_MINUTES} minutes',))

        recovered = cur.rowcount
        conn.commit()

        if recovered:
            logger.warning(f"Recovered {recovered} stuck jobs")

    finally:
        cur.close()
        conn.close()


# ==========================================================
# FETCH JOB
# ==========================================================

def fetch_next_matching_job():
    conn = get_db_conn()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT 
                q.id,
                q.jobid,   -- ✅ FIXED
                p.job_title,
                p.job_description,
                p.posted_by,
                q.attempts
            FROM job_matching_queue q
            JOIN job_postings p ON q.jobid::int = p.id
            WHERE q.status='PENDING'
            AND (q.next_attempt_at IS NULL OR q.next_attempt_at <= NOW())
            ORDER BY q.created_at
            LIMIT 1
            FOR UPDATE SKIP LOCKED
        """)

        row = cur.fetchone()

        if not row:
            conn.rollback()
            return None

        queue_id, job_id, title, jd, email, attempts = row

        cur.execute("""
            UPDATE job_matching_queue
            SET status='PROCESSING',
                locked_at=NOW(),
                locked_by=%s
            WHERE id=%s
        """, (WORKER_ID, queue_id))

        conn.commit()

        return queue_id, job_id, title, jd, email, attempts

    except Exception:
        conn.rollback()
        logger.exception("Failed to fetch matching job")
        return None

    finally:
        cur.close()
        conn.close()


# ==========================================================
# MARK DONE
# ==========================================================

def mark_done(queue_id):
    conn = get_db_conn()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE job_matching_queue
            SET status='DONE',
                locked_at=NULL,
                locked_by=NULL,
                last_error=NULL
            WHERE id=%s
        """, (queue_id,))
        conn.commit()
    finally:
        cur.close()
        conn.close()


# ==========================================================
# MARK FAILED
# ==========================================================

def mark_failed(queue_id, attempts, error):
    conn = get_db_conn()
    cur = conn.cursor()

    try:
        attempts += 1

        if attempts >= MAX_RETRIES:
            cur.execute("""
                UPDATE job_matching_queue
                SET status='FAILED',
                    attempts=%s,
                    last_error=%s,
                    locked_at=NULL,
                    locked_by=NULL
                WHERE id=%s
            """, (attempts, str(error), queue_id))
        else:
            next_try = datetime.utcnow() + timedelta(seconds=RETRY_DELAY_SECONDS)

            cur.execute("""
                UPDATE job_matching_queue
                SET status='PENDING',
                    attempts=%s,
                    next_attempt_at=%s,
                    last_error=%s,
                    locked_at=NULL,
                    locked_by=NULL
                WHERE id=%s
            """, (attempts, next_try, str(error), queue_id))

        conn.commit()

    finally:
        cur.close()
        conn.close()


# ==========================================================
# WORKER EXECUTION
# ==========================================================

def worker_execute():
    job = fetch_next_matching_job()

    if not job:
        return

    queue_id, job_id, title, jd, email, attempts = job

    logger.info(f"[{WORKER_ID}] MATCHING START → {title}")

    try:
        process_job_matching(title, jd, email, job_id)
        mark_done(queue_id)
        logger.info(f"[{WORKER_ID}] MATCHING DONE → {title}")

    except Exception as e:
        logger.exception("Job matching failed")
        mark_failed(queue_id, attempts, e)


# ==========================================================
# MAIN LOOP
# ==========================================================

def run_job_matching_parallel():
    logger.info("Parallel job matching worker started")

    executor = ThreadPoolExecutor(max_workers=MAX_MATCH_WORKERS)

    from api.app import shutdown_event

    while not shutdown_event.is_set():
        try:
            recover_stuck_jobs()

            for _ in range(MAX_MATCH_WORKERS):
                executor.submit(worker_execute)

        except Exception as e:
            logger.exception("Matching loop error - SAFE CONTINUE")

        time.sleep(POLL_INTERVAL)
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from api.db import get_db_conn
from api.workers.scoring_worker import process_submission

logger = logging.getLogger("scoring_queue_worker")

# -----------------------------------------
# CONFIG
# -----------------------------------------
MAX_PARALLEL_WORKERS = 5
POLL_INTERVAL = 2
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 60


# -----------------------------------------
# FETCH ONE LOCKED JOB
# -----------------------------------------
def fetch_next_submission():

    conn = get_db_conn()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT submission_id, attempts
            FROM scoring_queue
            WHERE status = 'PENDING'
              AND (next_attempt_at IS NULL OR next_attempt_at <= NOW())
            ORDER BY created_at
            LIMIT 1
            FOR UPDATE SKIP LOCKED
        """)

        row = cur.fetchone()

        if not row:
            conn.rollback()
            return None

        submission_id, attempts = row

        cur.execute("""
            UPDATE scoring_queue
            SET status = 'PROCESSING',
                locked_at = NOW()
            WHERE submission_id = %s
        """, (submission_id,))

        conn.commit()
        return submission_id, attempts

    except Exception:
        conn.rollback()
        logger.exception("Queue fetch failed")
        return None

    finally:
        cur.close()
        conn.close()


# -----------------------------------------
# MARK DONE
# -----------------------------------------
def mark_done(submission_id):

    conn = get_db_conn()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE scoring_queue
            SET status = 'DONE'
            WHERE submission_id = %s
        """, (submission_id,))
        conn.commit()

    finally:
        cur.close()
        conn.close()


# -----------------------------------------
# MARK FAILED + RETRY
# -----------------------------------------
def mark_failed(submission_id, attempts, error):

    conn = get_db_conn()
    cur = conn.cursor()

    try:
        if attempts + 1 >= MAX_RETRIES:
            status = "FAILED"
            next_attempt = None
        else:
            status = "PENDING"
            next_attempt = f"{RETRY_DELAY_SECONDS} seconds"

        if next_attempt:
            cur.execute("""
                UPDATE scoring_queue
                SET status=%s,
                    attempts=attempts+1,
                    last_error=%s,
                    next_attempt_at = NOW() + INTERVAL %s
                WHERE submission_id=%s
            """, (status, str(error), next_attempt, submission_id))
        else:
            cur.execute("""
                UPDATE scoring_queue
                SET status=%s,
                    attempts=attempts+1,
                    last_error=%s
                WHERE submission_id=%s
            """, (status, str(error), submission_id))

        conn.commit()

    finally:
        cur.close()
        conn.close()


# -----------------------------------------
# SINGLE WORKER EXECUTION
# -----------------------------------------
def worker_execute():

    job = fetch_next_submission()

    if not job:
        return

    submission_id, attempts = job

    logger.info(f"SCORING START → {submission_id}")

    try:
        process_submission(submission_id)
        mark_done(submission_id)
        logger.info(f"SCORING DONE → {submission_id}")

    except Exception as e:
        logger.exception(f"SCORING FAILED → {submission_id}")
        mark_failed(submission_id, attempts, e)


# -----------------------------------------
# PARALLEL WORKER LOOP
# -----------------------------------------
def run_queue_parallel():

    logger.info("Parallel scoring worker started")

    from api.app import shutdown_event   # adjust import path if needed

    while not shutdown_event.is_set():

        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS) as executor:
            futures = [
                executor.submit(worker_execute)
                for _ in range(MAX_PARALLEL_WORKERS)
            ]

            for f in futures:
                f.result()

        time.sleep(POLL_INTERVAL)
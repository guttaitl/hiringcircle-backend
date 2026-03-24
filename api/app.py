import threading
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

shutdown_event = threading.Event()
worker_threads = []


# ==========================================================
# WORKER STARTER (SAFE)
# ==========================================================
def start_workers_background():
    global worker_threads

    logger.info("🚀 Starting background workers (SAFE MODE)")

    from api.workers.resume_parsing_worker import process_resume_parsing
    from api.workers.queue_runner import run_queue_parallel
    from api.workers.job_matching_worker import run_job_matching_parallel
    from api.system_warmup import warmup_resume_index

    # ---------------- RESUME PARSER ---------------- #
    def resume_loop():
        logger.info("[WORKER] Resume parser started")
        while not shutdown_event.is_set():
            try:
                result = process_resume_parsing()

                if result.get("parsed", 0) == 0:
                    shutdown_event.wait(2)

            except Exception:
                logger.exception("[PARSER ERROR]")
                shutdown_event.wait(5)

    # ---------------- SCORING ---------------- #
    def scoring_loop():
        logger.info("[WORKER] Scoring started")
        try:
            run_queue_parallel()
        except Exception:
            logger.exception("[SCORING ERROR]")

    # ---------------- MATCHING ---------------- #
    def matching_loop():
        logger.info("[WORKER] Matching started")
        try:
            run_job_matching_parallel()
        except Exception:
            logger.exception("[MATCHING ERROR]")

    # ---------------- START THREADS ---------------- #
    workers = [
        ("Parser", resume_loop),
        ("Scoring", scoring_loop),
        ("Matching", matching_loop),
    ]

    for name, target in workers:
        t = threading.Thread(target=target, daemon=True)
        t.start()
        worker_threads.append(t)
        logger.info(f"✅ {name} worker started")

    # ---------------- WARMUP (NON-BLOCKING) ---------------- #
    def warmup_async():
        try:
            logger.info("[WARMUP] Running async warmup")
            warmup_resume_index()
            logger.info("[WARMUP] Completed")
        except Exception:
            logger.exception("[WARMUP ERROR]")

    threading.Thread(target=warmup_async, daemon=True).start()

    logger.info("✅ All workers running")


# ==========================================================
# STOP WORKERS
# ==========================================================
def stop_workers():
    shutdown_event.set()
    logger.info("🛑 Stopping workers")


# ==========================================================
# FASTAPI LIFESPAN (SAFE)
# ==========================================================
@asynccontextmanager
async def lifespan(app):
    logger.info("🚀 APP START")

    # Start workers safely (non-blocking)
    threading.Thread(target=start_workers_background, daemon=True).start()

    yield

    logger.info("🛑 APP SHUTDOWN")
    stop_workers()
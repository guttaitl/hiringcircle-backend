"""
Main Application Module for Hiring Circle API
Handles worker lifecycle and global state management
"""

import os
import sys
import threading
import logging
from contextlib import asynccontextmanager
import logging

# Suppress noisy libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==========================================================
# GLOBAL SHUTDOWN EVENT (for graceful worker termination)
# ==========================================================
shutdown_event = threading.Event()

# ==========================================================
# WORKER THREADS
# ==========================================================
worker_threads = []

# ==========================================================
# START ALL WORKERS
# ==========================================================
def start_all_workers():
    """Start all background worker threads"""
    global worker_threads
    
    logger.info("=" * 60)
    logger.info("STARTING ALL BACKGROUND WORKERS")
    logger.info("=" * 60)
    
    # Import workers here to avoid circular imports
    from api.workers.resume_parsing_worker import process_resume_parsing
    from api.workers.queue_runner import run_queue_parallel
    from api.workers.job_matching_worker import run_job_matching_parallel
    from api.workers.system_warmup import warmup_resume_index
    
    # ==========================================================
    # 1. RESUME PARSING WORKER
    # ==========================================================
    def resume_parsing_loop():
        """Continuously parse pending resumes"""
        logger.info("[WORKER] Resume parsing worker started")
        while not shutdown_event.is_set():
            try:
                result = process_resume_parsing()
                if result.get("parsed", 0) == 0 and result.get("skipped", 0) == 0:
                    # No work to do, sleep briefly
                    shutdown_event.wait(2)
                else:
                    logger.info(f"[PARSER] Processed: {result}")
            except Exception as e:
                logger.exception(f"[PARSER] Error in parsing loop: {e}")
                shutdown_event.wait(5)
    
    # ==========================================================
    # 2. SCORING QUEUE WORKER
    # ==========================================================
    def scoring_loop():
        """Process scoring queue"""
        logger.info("[WORKER] Scoring worker started")
        try:
            run_queue_parallel()
        except Exception as e:
            logger.exception(f"[SCORING] Error in scoring loop: {e}")
    
    # ==========================================================
    # 3. JOB MATCHING WORKER
    # ==========================================================
    def job_matching_loop():
        """Process job matching queue"""
        logger.info("[WORKER] Job matching worker started")
        try:
            run_job_matching_parallel()
        except Exception as e:
            logger.exception(f"[MATCHING] Error in job matching loop: {e}")
    
    # ==========================================================
    # START WORKER THREADS
    # ==========================================================
    workers = [
        ("ResumeParser", resume_parsing_loop),
        ("ScoringQueue", scoring_loop),
        ("JobMatching", job_matching_loop),
    ]
    
    for name, target in workers:
        thread = threading.Thread(target=target, name=f"Worker-{name}", daemon=True)
        thread.start()
        worker_threads.append(thread)
        logger.info(f"[STARTED] {name} worker thread")
    
    # ==========================================================
    # RUN SYSTEM WARMUP (INDEXING)
    # ==========================================================
    logger.info("[WARMUP] Running system warmup...")
    try:
        warmup_resume_index()
        logger.info("[WARMUP] System warmup completed successfully")
    except Exception as e:
        logger.exception(f"[WARMUP] System warmup failed: {e}")
    
    logger.info("=" * 60)
    logger.info("ALL WORKERS STARTED SUCCESSFULLY")
    logger.info("=" * 60)

# ==========================================================
# STOP ALL WORKERS
# ==========================================================
def stop_all_workers():
    """Signal all workers to stop and wait for them to finish"""
    global worker_threads
    
    logger.info("=" * 60)
    logger.info("STOPPING ALL WORKERS...")
    logger.info("=" * 60)
    
    # Signal shutdown
    shutdown_event.set()
    
    # Wait for all threads to finish (with timeout)
    for thread in worker_threads:
        if thread.is_alive():
            logger.info(f"[STOPPING] Waiting for {thread.name}...")
            thread.join(timeout=10)
            if thread.is_alive():
                logger.warning(f"[TIMEOUT] {thread.name} did not stop in time")
    
    worker_threads = []
    logger.info("[STOPPED] All workers stopped")

# ==========================================================
# LIFESPAN CONTEXT MANAGER (for FastAPI)
# ==========================================================
@asynccontextmanager
async def lifespan(app):
    """FastAPI lifespan context manager for startup/shutdown"""
    # Startup
    logger.info("=" * 60)
    logger.info("APPLICATION STARTUP")
    logger.info("=" * 60)
    
    # Start workers in a separate thread
    startup_thread = threading.Thread(target=start_all_workers, name="Startup-Workers", daemon=True)
    startup_thread.start()
    
    yield
    
    # Shutdown
    logger.info("=" * 60)
    logger.info("APPLICATION SHUTDOWN")
    logger.info("=" * 60)
    stop_all_workers()

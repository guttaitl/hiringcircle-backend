import logging
import time
import json
import numpy as np

from api.db import get_db_conn
from api.workers.resume_parsing_worker import process_resume_parsing
from api.ai.embeddings import get_embedding
from api.core.startup_stats import startup_stats
import threading
from api.workers.resume_scanner import start_scanner
from api.faiss_index import ResumeVectorIndex

logger = logging.getLogger("system_warmup")

EXPECTED_EMBEDDING_DIM = 1536

# GLOBAL SINGLETON
resume_vector_index = ResumeVectorIndex()


# =========================================================
# GETTER
# =========================================================
def get_resume_vector_index():
    return resume_vector_index


# =========================================================
# PARSE EMBEDDING SAFELY
# =========================================================
def parse_embedding(emb_raw):
    if emb_raw is None:
        return None

    try:
        if isinstance(emb_raw, str):
            emb = json.loads(emb_raw)
        elif isinstance(emb_raw, list):
            emb = emb_raw
        else:
            return None

        if len(emb) != EXPECTED_EMBEDDING_DIM:
            return None

        return np.asarray(emb, dtype="float32")

    except Exception:
        return None


# =========================================================
# GENERATE EMBEDDINGS (BATCH OPTIMIZED)
# =========================================================
def generate_missing_embeddings(cur):
    logger.info("Generating missing embeddings...")

    cur.execute("""
        SELECT id, resume_text
        FROM candidate_resumes
        WHERE embedding IS NULL
        AND resume_text IS NOT NULL
    """)

    rows = cur.fetchall() or []

    if not rows:
        return 0

    generated = 0

    for rid, text in rows:
        try:
            emb = get_embedding(text)

            if not emb or len(emb) != EXPECTED_EMBEDDING_DIM:
                continue

            cur.execute("""
                UPDATE candidate_resumes
                SET embedding = %s
                WHERE id = %s
            """, (emb, rid))

            generated += 1

        except Exception:
            logger.exception(f"Embedding failed for resume {rid}")

    return generated


# =========================================================
# LOAD EMBEDDINGS FROM DB
# =========================================================
def load_embeddings(cur):
    logger.info("Loading embeddings from DB...")

    cur.execute("""
        SELECT id, embedding
        FROM candidate_resumes
        WHERE embedding IS NOT NULL
    """)

    rows = cur.fetchall() or []

    resume_ids = []
    embeddings = []
    invalid = 0

    for rid, emb_raw in rows:
        emb = parse_embedding(emb_raw)

        if emb is None:
            invalid += 1
            continue

        resume_ids.append(rid)
        embeddings.append(emb)

    return embeddings, resume_ids, invalid


# =========================================================
# MAIN WARMUP
# =========================================================
def warmup_resume_index():
    start_time = time.time()   # ✅ FIX
    logger.info("WARMUP STARTED")
    conn = get_db_conn()
    cur = conn.cursor()

    try:
        # -------------------------------------------------
        # LOAD EXISTING FAISS INDEX (FAST START)
        # -------------------------------------------------
        resume_vector_index.load()

        if resume_vector_index.is_ready():
            logger.info("FAISS already loaded from disk → skipping rebuild")
            return

        # -------------------------------------------------
        # TOTAL COUNT
        # -------------------------------------------------
        cur.execute("SELECT COUNT(*) FROM candidate_resumes")
        startup_stats["total_resumes"] = cur.fetchone()[0]

        # -------------------------------------------------
        # PARSE NEW RESUMES
        # -------------------------------------------------
        logger.info("Parsing resumes...")
        result = process_resume_parsing()
        parsed_now = result.get("parsed", 0)

        logger.info(f"Parsed resumes this run: {parsed_now}")

        cur.execute("""
            SELECT COUNT(*) FROM candidate_resumes
            WHERE parsed_successfully = true
        """)
        startup_stats["parsed_resumes"] = cur.fetchone()[0]

        # -------------------------------------------------
        # GENERATE EMBEDDINGS
        # -------------------------------------------------
        generated = generate_missing_embeddings(cur)
        conn.commit()

        logger.info(f"Generated embeddings: {generated}")

        cur.execute("""
            SELECT COUNT(*) FROM candidate_resumes
            WHERE embedding IS NOT NULL
        """)
        startup_stats["embeddings_ready"] = cur.fetchone()[0]

        # -------------------------------------------------
        # LOAD EMBEDDINGS
        # -------------------------------------------------
        embeddings, resume_ids, invalid = load_embeddings(cur)

        startup_stats["indexed_resumes"] = len(embeddings)

        if not embeddings:
            logger.warning("No embeddings found → FAISS not built")
            return

        # -------------------------------------------------
        # BUILD INDEX
        # -------------------------------------------------
        logger.info("Building FAISS index...")

        resume_vector_index.build(embeddings, resume_ids)

        logger.info(f"FAISS ready with {len(embeddings)} vectors")

        # -------------------------------------------------
        # STATS
        # -------------------------------------------------
        startup_stats["warmup_time_sec"] = round(
            time.time() - start_time, 2
        )

        logger.info("========== STARTUP STATS ==========")
        logger.info(f"Total resumes    : {startup_stats['total_resumes']}")
        logger.info(f"Parsed resumes   : {startup_stats['parsed_resumes']}")
        logger.info(f"Embeddings ready : {startup_stats['embeddings_ready']}")
        logger.info(f"Indexed FAISS    : {startup_stats['indexed_resumes']}")
        logger.info(f"Warmup time      : {startup_stats['warmup_time_sec']} sec")
        logger.info("===================================")

    except Exception:
        logger.exception("Warmup failed")

    finally:
        cur.close()
        conn.close()


# =========================================================
# MANUAL RUN
# =========================================================
if __name__ == "__main__":
    warmup_resume_index()
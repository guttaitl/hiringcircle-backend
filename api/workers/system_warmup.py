import logging
import time
import json
import numpy as np

from api.db import get_db_conn
from api.workers.resume_parsing_worker import process_resume_parsing
from api.ai.embeddings import get_embedding
from api.core.startup_stats import startup_stats

# FAISS index
from api.faiss_index import ResumeVectorIndex

logger = logging.getLogger("system_warmup")

# =========================================================
# CONFIG
# =========================================================
EXPECTED_EMBEDDING_DIM = 1536

# =========================================================
# GLOBAL FAISS INDEX (SINGLE INSTANCE)
# =========================================================
resume_vector_index = ResumeVectorIndex()


# =========================================================
# GETTER (USED BY MATCHING ENGINE)
# =========================================================
def get_resume_vector_index():
    return resume_vector_index


# =========================================================
# HELPER — SAFE EMBEDDING LOAD
# =========================================================
def parse_embedding(emb_raw):
    if emb_raw is None:
        return None

    if isinstance(emb_raw, str):
        emb = json.loads(emb_raw)
    elif isinstance(emb_raw, list):
        emb = emb_raw
    else:
        raise ValueError(f"Unsupported embedding type: {type(emb_raw)}")

    if len(emb) != EXPECTED_EMBEDDING_DIM:
        raise ValueError(
            f"Invalid embedding dimension {len(emb)} "
            f"(expected {EXPECTED_EMBEDDING_DIM})"
        )

    return np.asarray(emb, dtype="float32")


# =========================================================
# WARMUP (FAST + INCREMENTAL)
# =========================================================
def warmup_resume_index():

    logger.info("System warmup starting...")
    start_time = time.time()

    conn = get_db_conn()
    cur = conn.cursor()

    try:

        # -------------------------------------------------
        # TOTAL RESUMES
        # -------------------------------------------------
        cur.execute("SELECT COUNT(*) FROM candidate_resumes")
        total = cur.fetchone()[0]
        startup_stats["total_resumes"] = total

        # -------------------------------------------------
        # PARSE ONLY PENDING (NO LOOP)
        # -------------------------------------------------
        logger.info("Parsing pending resumes...")

        result = process_resume_parsing()
        parsed_now = result.get("parsed", 0)

        logger.info(f"Parsed resumes this run: {parsed_now}")

        # COUNT PARSED
        cur.execute("""
            SELECT COUNT(*)
            FROM candidate_resumes
            WHERE parsed_successfully = true
        """)
        startup_stats["parsed_resumes"] = cur.fetchone()[0]

        # -------------------------------------------------
        # GENERATE ONLY MISSING EMBEDDINGS
        # -------------------------------------------------
        logger.info("Generating missing embeddings...")

        cur.execute("""
            SELECT id, resume_text
            FROM candidate_resumes
            WHERE embedding IS NULL
            AND resume_text IS NOT NULL
        """)

        missing = cur.fetchall() or []

        generated = 0

        for rid, text in missing:
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

        conn.commit()

        logger.info(f"Generated embeddings: {generated}")

        # -------------------------------------------------
        # COUNT EMBEDDINGS
        # -------------------------------------------------
        cur.execute("""
            SELECT COUNT(*)
            FROM candidate_resumes
            WHERE embedding IS NOT NULL
        """)
        startup_stats["embeddings_ready"] = cur.fetchone()[0]

        # -------------------------------------------------
        # LOAD EMBEDDINGS INTO MEMORY
        # -------------------------------------------------
        logger.info("Loading embeddings into memory...")

        cur.execute("""
            SELECT id, embedding
            FROM candidate_resumes
            WHERE embedding IS NOT NULL
        """)

        rows = cur.fetchall() or []

        resume_ids = []
        embeddings = []
        invalid_count = 0

        for rid, emb_raw in rows:
            try:
                emb = parse_embedding(emb_raw)
                if emb is None:
                    continue

                embeddings.append(emb)
                resume_ids.append(rid)

            except Exception:
                invalid_count += 1
                logger.exception(f"Invalid embedding for resume {rid}")

        startup_stats["indexed_resumes"] = len(embeddings)

        if not embeddings:
            logger.warning("No embeddings found to build FAISS index")
            return

        # -------------------------------------------------
        # BUILD FAISS INDEX
        # -------------------------------------------------
        logger.info("Building FAISS vector index...")

        resume_vector_index.build(embeddings, resume_ids)

        logger.info(
            f"FAISS index ready with {len(embeddings)} vectors "
            f"(skipped {invalid_count} invalid)"
        )

        startup_stats["warmup_time_sec"] = round(
            time.time() - start_time, 2
        )

        # -------------------------------------------------
        # STATS
        # -------------------------------------------------
        logger.info("========== STARTUP ANALYTICS ==========")
        logger.info(f"Total resumes        : {startup_stats['total_resumes']}")
        logger.info(f"Parsed resumes       : {startup_stats['parsed_resumes']}")
        logger.info(f"Embeddings ready     : {startup_stats['embeddings_ready']}")
        logger.info(f"Indexed in FAISS     : {startup_stats['indexed_resumes']}")
        logger.info(f"Warmup time (sec)    : {startup_stats['warmup_time_sec']}")
        logger.info("=======================================")

    finally:
        cur.close()
        conn.close()


# =========================================================
# MANUAL RUN (OPTIONAL)
# =========================================================
if __name__ == "__main__":
    warmup_resume_index()
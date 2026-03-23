import os
import json
import hashlib
import logging
from typing import Optional

from api.db import get_db_conn
from api.resume_parser import parse_resume
from api.ai.embeddings import get_embedding
from api.utils.doc_converter import convert_doc_to_docx


logger = logging.getLogger("resume_parser")

BATCH_SIZE = 5
PROJECT_ROOT = os.path.abspath(os.getcwd())


# ==========================================================
# PATH RESOLUTION
# ==========================================================
def resolve_resume_path(file_path: Optional[str]) -> Optional[str]:
    if not file_path:
        return None

    file_path = file_path.replace("\\", os.sep).replace("/", os.sep)

    if os.path.isabs(file_path):
        return file_path

    return os.path.join(PROJECT_ROOT, file_path)


# ==========================================================
# FAILURE MARKER
# ==========================================================
def mark_failed(cur, rid, reason: str):
    logger.warning(f"[PARSER] mark_failed resume_id={rid} reason={reason}")

    cur.execute("""
        UPDATE candidate_resumes
        SET
            parsed_successfully = false,
            parse_error = %s,
            last_parsed_at = NOW(),
            updated_at = NOW()
        WHERE id = %s
    """, (reason, rid))


# ==========================================================
# MAIN WORKER
# ==========================================================
def process_resume_parsing():

    conn = get_db_conn()
    cur = conn.cursor()

    parsed = 0
    skipped = 0
    failed = 0

    try:
        # --------------------------------------------------
        # FETCH PENDING RESUMES
        # --------------------------------------------------
        sql = """
            SELECT id, file_path, parse_hash
            FROM candidate_resumes
            WHERE parsed_successfully IS DISTINCT FROM true
            AND parse_error IS NULL
            AND (
                resume_text IS NULL
                OR resume_text = ''
                OR resume_text LIKE 'Resume parsing pending%%'
            )
            ORDER BY updated_at NULLS FIRST
            LIMIT %s
        """

        cur.execute(sql, (int(BATCH_SIZE),))
        rows = cur.fetchall()

        if not rows:
            logger.debug("[PARSER] nothing to process")
            return {"parsed": 0, "skipped": 0, "failed": 0}

        logger.info(f"[PARSER] processing batch size={len(rows)}")

        # --------------------------------------------------
        # PROCESS EACH RESUME
        # --------------------------------------------------
        for rid, file_path, existing_hash in rows:

            try:
                abs_path = resolve_resume_path(file_path)

                # ------------------------------------------
                # FILE EXISTS
                # ------------------------------------------
                if not abs_path or not os.path.exists(abs_path):
                    mark_failed(cur, rid, "FILE_MISSING")
                    skipped += 1
                    continue

                # ------------------------------------------
                # DOC → DOCX CONVERSION
                # ------------------------------------------
                try:
                    abs_path = convert_doc_to_docx(abs_path)
                except Exception as e:
                    logger.warning(f"[PARSER] conversion failed {abs_path} | {e}")
                    mark_failed(cur, rid, "DOC_CONVERSION_FAILED")
                    skipped += 1
                    continue

                # ------------------------------------------
                # READ FILE
                # ------------------------------------------
                try:
                    with open(abs_path, "rb") as f:
                        file_bytes = f.read()
                except Exception as e:
                    mark_failed(cur, rid, f"FILE_READ_ERROR:{e}")
                    skipped += 1
                    continue

                # ------------------------------------------
                # PARSE TEXT
                # ------------------------------------------
                try:
                    text = parse_resume(
                        file_bytes=file_bytes,
                        filename=abs_path
                    )
                except Exception as e:
                    logger.warning(f"[PARSER] parse failed {abs_path} | {e}")
                    mark_failed(cur, rid, f"PARSE_ERROR:{e}")
                    skipped += 1
                    continue

                if not text or not text.strip():
                    mark_failed(cur, rid, "EMPTY_TEXT")
                    skipped += 1
                    continue

                # ------------------------------------------
                # STORE TEXT
                # ------------------------------------------
                parse_hash = hashlib.sha256(text.encode()).hexdigest()

                cur.execute("""
                    UPDATE candidate_resumes
                    SET
                        resume_text = %s,
                        parsed_successfully = true,
                        parse_error = NULL,
                        last_parsed_at = NOW(),
                        updated_at = NOW()
                    WHERE id = %s
                """, (text, rid))

                # ------------------------------------------
                # UPDATE SUBMISSION SNAPSHOT
                # ------------------------------------------
                cur.execute("""
                    UPDATE submissions
                    SET resume_text = %s
                    WHERE resume_id = %s
                """, (text, rid))

                # ------------------------------------------
                # EMBEDDING ONLY IF TEXT CHANGED
                # ------------------------------------------
                if existing_hash != parse_hash:
                    try:
                        embedding = get_embedding(text)

                        cur.execute("""
                            UPDATE candidate_resumes
                            SET
                                embedding = %s,
                                embedding_model = 'text-embedding-3-small',
                                indexed_at = NOW(),
                                parse_hash = %s
                            WHERE id = %s
                        """, (json.dumps(embedding), parse_hash, rid))

                    except Exception as e:
                        logger.exception(f"[PARSER] embedding failed rid={rid}")
                        mark_failed(cur, rid, f"EMBEDDING_ERROR:{e}")
                        failed += 1
                        continue

                # ------------------------------------------
                # QUEUE SCORING
                # ------------------------------------------
                cur.execute("""
                    INSERT INTO scoring_queue (submission_id, status, created_at)
                    SELECT s.submission_id, 'PENDING', NOW()
                    FROM submissions s
                    WHERE s.resume_id = %s
                      AND s.scoring_status = 'PENDING'
                      AND NOT EXISTS (
                          SELECT 1 FROM scoring_queue q
                          WHERE q.submission_id = s.submission_id
                      )
                """, (rid,))

                parsed += 1

            except Exception as e:
                logger.exception(f"[PARSER] unexpected crash resume_id={rid}")
                mark_failed(cur, rid, f"UNHANDLED:{e}")
                failed += 1

        # --------------------------------------------------
        # COMMIT BATCH
        # --------------------------------------------------
        conn.commit()

        logger.info(
            f"[PARSER DONE] parsed={parsed} skipped={skipped} failed={failed}"
        )

        return {
            "parsed": parsed,
            "skipped": skipped,
            "failed": failed
        }

    except Exception:
        conn.rollback()
        logger.exception("[PARSER] worker fatal crash")
        return {"parsed": 0, "skipped": 0, "failed": 0}

    finally:
        cur.close()
        conn.close()
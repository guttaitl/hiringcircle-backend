import logging
from datetime import datetime
import uuid

from api.db import get_db_conn, SessionLocal
from api.email_service import send_shortlist_email
from api.ai.vector_utils import cosine_similarity, load_embedding
from api.ai.embeddings import get_embedding
from api.ai.domain_intelligence import detect_domains, domain_similarity
from api.utils.report_builder import build_basic_report
from api.models import Submission
from api.services.ai_scoring import compute_structured_score

from api.workers.system_warmup import get_resume_vector_index

logger = logging.getLogger("perfect_match_engine")

VECTOR_WEIGHT = 0.75
DOMAIN_WEIGHT = 0.25


# =========================================================
# SAVE MATCHES
# =========================================================
def save_matches(conn, jobid, matches):
    cur = conn.cursor()

    try:
        cur.execute("SELECT id FROM job_postings WHERE jobid=%s", (jobid,))
        job = cur.fetchone()

        if not job:
            logger.warning(f"Job not found for jobid={jobid}")
            return

        job_internal_id = job[0]

        for m in matches:
            cur.execute("""
                INSERT INTO ai_matches (
                    match_id,
                    job_posting_id,
                    resume_id,
                    match_score,
                    skill_match_score,
                    experience_match_score,
                    overall_fit,
                    reasoning,
                    created_by,
                    created_at
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
            """, (
                str(uuid.uuid4()),
                job_internal_id,
                m["resume_id"],
                m["match_score"],
                m["skill_score"],
                m["experience_score"],
                m["overall_fit"],
                m["reasoning"],
                "worker"
            ))

        conn.commit()
        logger.info("Matches saved")

    except Exception:
        logger.exception("Save matches failed")


# =========================================================
# MAIN MATCHING ENGINE
# =========================================================
def process_job_matching(job_title, job_description, poster_email, jobid):

    logger.info("========================================")
    logger.info("MATCHING STARTED: %s", job_title)

    if not job_description:
        logger.warning("Empty job description")
        return

    conn = get_db_conn()
    cur = conn.cursor()
    session = SessionLocal()

    try:
        # -------------------------------------------------
        # EMBEDDING (SAFE)
        # -------------------------------------------------
        job_embedding = get_embedding(job_description)

        if not job_embedding:
            logger.error("Job embedding failed")
            return

        job_domains = detect_domains(job_description)

        # -------------------------------------------------
        # FAISS SEARCH (SAFE)
        # -------------------------------------------------
        resume_vector_index = get_resume_vector_index()

        if not resume_vector_index or not resume_vector_index.is_ready():
            logger.warning("FAISS index not ready")
            return

        candidate_ids = resume_vector_index.search(job_embedding, top_k=50)

        if not candidate_ids:
            logger.warning("No candidates found")
            return

        # -------------------------------------------------
        # FETCH ONLY REQUIRED DATA
        # -------------------------------------------------
        placeholders = ",".join(["%s"] * len(candidate_ids))

        cur.execute(f"""
            SELECT id, embedding, file_path, full_name, resume_text
            FROM candidate_resumes
            WHERE id IN ({placeholders})
        """, tuple(candidate_ids))

        rows = cur.fetchall()
        if not rows:
            return

        # -------------------------------------------------
        # FAST RANKING (NO AI YET)
        # -------------------------------------------------
        ranked = []

        for rid, emb_json, resume_path, name, resume_text in rows:

            emb = load_embedding(emb_json)
            if not emb:
                continue

            vector_score = cosine_similarity(job_embedding, emb) * 100

            resume_domains = detect_domains(resume_text or "")
            domain_score = domain_similarity(job_domains, resume_domains)

            if domain_score <= 1:
                domain_score *= 100

            final_score = (
                vector_score * VECTOR_WEIGHT +
                domain_score * DOMAIN_WEIGHT
            )

            ranked.append((final_score, rid, resume_path, name, resume_text))

        if not ranked:
            return

        ranked.sort(reverse=True)

        # 👉 ONLY TOP 5 go to AI scoring
        top_candidates = ranked[:5]

        matches = []
        email_payload = []

        # -------------------------------------------------
        # AI SCORING (LIMITED)
        # -------------------------------------------------
        for score, rid, resume_path, name, resume_text in top_candidates:

            sem_score, similarity, _ = compute_structured_score(
                resume_text,
                job_description
            )

            matches.append({
                "resume_id": rid,
                "match_score": sem_score,
                "skill_score": sem_score,
                "experience_score": similarity,
                "overall_fit": "Good Fit",
                "reasoning": "AI evaluated match"
            })

            sub = session.query(Submission)\
                .filter(Submission.resume_id == rid)\
                .order_by(Submission.created_at.desc())\
                .first()

            if sub:
                sub.match_score = sem_score
                sub.semantic_similarity = similarity
                report_path = build_basic_report(sub)
            else:
                report_path = None

            email_payload.append((
                sem_score,
                rid,
                resume_path,
                report_path,
                name,
                None
            ))

        # -------------------------------------------------
        # SAVE + EMAIL
        # -------------------------------------------------
        save_matches(conn, jobid, matches)

        send_shortlist_email(
            poster_email,
            job_title,
            email_payload
        )

        logger.info("MATCHING COMPLETED")

    except Exception:
        logger.exception("Matching engine failed")

    finally:
        session.close()
        cur.close()
        conn.close()
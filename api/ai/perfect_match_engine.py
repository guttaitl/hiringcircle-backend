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
# SAVE MATCHES TO DB (NEW)
# =========================================================
def save_matches(conn, jobid, matches):
    cur = conn.cursor()

    try:
        # get internal job id
        cur.execute(
            "SELECT id FROM job_postings WHERE jobid=%s",
            (jobid,)
        )
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
                str(uuid.uuid4()),   # 🔥 THIS FIXES YOUR ISSUE
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
        logger.info("Matches saved to database")

    except Exception as e:
        logger.exception("Failed to save matches: %s", e)


# =========================================================
# TEMP EVALUATION OBJECT
# =========================================================
class TempEvaluation:

    def __init__(
        self,
        resume_id,
        name,
        resume_text,
        job_title,
        job_description,
        score,
        similarity
    ):
        self.submission_id = f"TEMP-{resume_id}"
        self.resume_id = resume_id
        self.candidate_name = name or "Candidate"
        self.full_name = name or "Candidate"
        self.job_id = job_title
        self.job_title = job_title
        self.job_description = job_description
        self.resume_text = resume_text
        self.match_score = round(float(score), 2)
        self.semantic_similarity = similarity

        if score >= 90:
            self.final_recommendation = "Recommended for interview"
        elif score >= 75:
            self.final_recommendation = "Consider for screening"
        else:
            self.final_recommendation = "Not recommended"

        self.processed_at = datetime.utcnow()
        self.report_path = None


# =========================================================
# MAIN MATCHING ENGINE (UPDATED)
# =========================================================
def process_job_matching(job_title, job_description, poster_email, jobid):
    resume_vector_index = get_resume_vector_index()
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
        # EMBEDDING
        # -------------------------------------------------
        job_embedding = get_embedding(job_description)
        job_domains = detect_domains(job_description)

        # -------------------------------------------------
        # SEARCH
        # -------------------------------------------------
        resume_vector_index = get_resume_vector_index()

        if not resume_vector_index:
            logger.error("❌ FAISS index not initialized - no resumes indexed")
            return

        candidate_ids = resume_vector_index.search(job_embedding, top_k=100)

        if not candidate_ids:
            logger.warning("No candidates found")
            return

        placeholders = ",".join(["%s"] * len(candidate_ids))

        cur.execute(f"""
            SELECT id, embedding, file_path, full_name, resume_text
            FROM candidate_resumes
            WHERE id IN ({placeholders})
        """, tuple(candidate_ids))

        rows = cur.fetchall()
        if not rows:
            logger.warning("No resumes loaded")
            return

        # -------------------------------------------------
        # RANKING
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

            final_score = vector_score * VECTOR_WEIGHT + domain_score * DOMAIN_WEIGHT

            ranked.append((final_score, rid, resume_path, name, resume_text))

        ranked.sort(reverse=True)
        top_candidates = ranked[:3]

        # -------------------------------------------------
        # MATCH STORAGE PREP
        # -------------------------------------------------
        matches = []
        email_payload = []

        # -------------------------------------------------
        # PROCESS CANDIDATES
        # -------------------------------------------------
        for score, rid, resume_path, name, resume_text in top_candidates:

            sem_score, similarity, breakdown = compute_structured_score(
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

            # report
            sub = session.query(Submission)\
                .filter(Submission.resume_id == rid)\
                .order_by(Submission.created_at.desc())\
                .first()

            if sub:
                sub.match_score = sem_score
                sub.semantic_similarity = similarity
                report_path = build_basic_report(sub)
            else:
                temp = TempEvaluation(
                    rid, name, resume_text,
                    job_title, job_description,
                    score, similarity
                )
                report_path = build_basic_report(temp)

            email_payload.append((
                sem_score,
                rid,
                resume_path,
                report_path,
                name,
                None
            ))

        # -------------------------------------------------
        # SAVE MATCHES (NEW)
        # -------------------------------------------------
        save_matches(conn, jobid, matches)

        # -------------------------------------------------
        # EMAIL
        # -------------------------------------------------
        send_shortlist_email(
            poster_email,
            job_title,
            email_payload
        )

        logger.info("MATCHING COMPLETED")

    except Exception as e:
        logger.exception("Matching engine error: %s", e)

    finally:
        session.close()
        cur.close()
        conn.close()
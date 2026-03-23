import logging
from datetime import datetime

from api.db import SessionLocal
from api.utils.report_builder import build_basic_report
from api.services.ai_scoring import compute_structured_score

logger = logging.getLogger("scoring_worker")


# ==========================================================
# RECOMMENDATION ENGINE (BASED ON SEMANTIC SCORE)
# ==========================================================

def _derive_recommendation(score: float):
    """
    Convert semantic score into recruiter decision.
    """

    if score >= 90:
        return (
            "Strong semantic alignment with job requirements.",
            "HIGH",
            "Recommended for technical interview"
        )

    elif score >= 75:
        return (
            "Good alignment with job requirements.",
            "MEDIUM",
            "Consider for screening discussion"
        )

    else:
        return (
            "Limited alignment with role requirements.",
            "LOW",
            "Not recommended"
        )


# ==========================================================
# MAIN WORKER ENTRY
# ==========================================================

def process_submission(submission_id: str):
    # LAZY IMPORT - Prevents circular dependency
    from api.models import Submission

    logger.info("===================================")
    logger.info("SCORING SUBMISSION: %s", submission_id)

    session = SessionLocal()

    try:
        # --------------------------------------------------
        # LOAD SUBMISSION
        # --------------------------------------------------
        sub = session.query(Submission).filter(
            Submission.submission_id == submission_id
        ).first()

        if not sub:
            logger.warning("Submission not found")
            return

        logger.info("Loaded submission")

        # --------------------------------------------------
        # RUN STRUCTURED SCORING ENGINE
        # --------------------------------------------------
        score, similarity, breakdown = compute_structured_score(
            sub.resume_text or "",
            sub.job_description or ""
        )

        sub.match_score = score
        sub.semantic_similarity = similarity
        sub.score_breakdown = breakdown

        # --------------------------------------------------
        # FITMENT SUMMARY + RECOMMENDATION
        # --------------------------------------------------
        if score >= 90:
            sub.fit_summary = "Candidate demonstrates excellent alignment with job requirements."
            sub.confidence_band = "HIGH"
            sub.final_recommendation = "Strongly recommended for interview"

        elif score >= 75:
            sub.fit_summary = "Candidate shows good alignment with job requirements."
            sub.confidence_band = "MEDIUM"
            sub.final_recommendation = "Recommended for screening"

        elif score >= 60:
            sub.fit_summary = "Candidate shows partial alignment with job requirements."
            sub.confidence_band = "LOW"
            sub.final_recommendation = "Consider for further review"

        else:
            sub.fit_summary = "Candidate shows limited alignment with role requirements."
            sub.confidence_band = "LOW"
            sub.final_recommendation = "Not recommended"
        # --------------------------------------------------
        # RECOMMENDATION + CONFIDENCE
        # --------------------------------------------------
        fit_summary, confidence, recommendation = _derive_recommendation(score)

        # --------------------------------------------------
        # UPDATE SUBMISSION
        # --------------------------------------------------
        sub.match_score = score
        sub.semantic_similarity = similarity

        sub.fit_summary = fit_summary
        sub.confidence_band = confidence
        sub.final_recommendation = recommendation

        # Optional fields (not used in semantic model yet)
        sub.skill_matrix = None
        sub.fabrication_observations = ""

        sub.scoring_status = "COMPLETED"
        sub.processed_at = datetime.utcnow()

        logger.info("Score stored: %.2f", sub.match_score)

        # --------------------------------------------------
        # GENERATE REPORT
        # --------------------------------------------------
        filename = build_basic_report(sub)
        sub.report_path = filename

        logger.info("Report generated: %s", filename)

        # --------------------------------------------------
        # SAVE
        # --------------------------------------------------
        session.commit()
        logger.info("SCORING COMPLETE")

    except Exception:
        session.rollback()
        logger.exception("SCORING FAILED")

    finally:
        session.close()
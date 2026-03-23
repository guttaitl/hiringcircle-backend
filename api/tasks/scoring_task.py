from api.core.celery_app import celery
from api.db import SessionLocal
from api.services.parallel_scoring import run_parallel
from api.services.scoring_logic import compute_score


@celery.task(bind=True, max_retries=3)
def score_submission(self, submission_id):
    session = SessionLocal()

    try:
        sub = load_submission(session, submission_id)

        sm, oa = run_parallel(
            sub.job_title,
            sub.job_description,
            sub.resume_text
        )

        compute_score(session, sub, sm, oa)

    except Exception as e:
        raise self.retry(exc=e, countdown=5)
    finally:
        session.close()

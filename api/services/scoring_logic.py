from datetime import datetime


def compute_score(session, sub, sm, oa):

    years = float(oa.estimated_years_experience)
    domain = float(oa.domain_match)
    responsibility = float(oa.responsibility_match)

    weights = {
        "EXPLICIT": 1.0,
        "IMPLICIT": 0.85,
        "PARTIAL": 0.7,
        "NO": 0.0,
    }

    required = [s for s in sm.skills if s.required]

    if not required:
        skill_score = 0
    else:
        skill_score = sum(
            weights.get(s.evidence, 0)
            for s in required
        ) / len(required) * 100

    final_score = (
        skill_score * 0.6
        + responsibility * 0.25
        + domain * 0.15
    )

    sub.skill_matrix = [s.model_dump() for s in sm.skills]
    sub.match_score = round(final_score)
    sub.scoring_status = "COMPLETED"
    sub.processed_at = datetime.utcnow()

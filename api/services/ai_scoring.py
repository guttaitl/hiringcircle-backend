import logging
import re
from typing import Tuple, Dict

from api.services.embedding_service import get_text_embedding
from api.ai.vector_utils import cosine_similarity
from api.services.semantic_matcher import semantic_match_score
from api.utils.openai_client import call_openai

logger = logging.getLogger("ai_scoring")


# =========================================================
# SCORING WEIGHTS (TUNE HERE)
# =========================================================
REQUIRED_WEIGHT = 0.60
OPTIONAL_WEIGHT = 0.15
RESPONSIBILITY_WEIGHT = 0.10
EXPERIENCE_WEIGHT = 0.10
SEMANTIC_WEIGHT = 0.05


# =========================================================
# EXTRACT SKILLS USING AI
# =========================================================
def extract_job_structure(job_text: str) -> Dict:

    prompt = f"""
You are a hiring expert.

Extract structured information from this job description.

Return ONLY valid JSON:

{{
  "required_skills": ["skill1", "skill2"],
  "optional_skills": ["skill3"],
  "responsibilities": ["short bullet 1", "short bullet 2"],
  "min_experience_years": number
}}

JOB DESCRIPTION:
{job_text}
"""

    return call_openai(
        messages=[{"role": "user", "content": prompt}],
        expect_json=True
    )


# =========================================================
# SKILL COVERAGE CALCULATION
# =========================================================
from api.services.semantic_matcher import semantic_match_score

def compute_skill_coverage(skills, resume_text):
    """
    Returns ratio of matched skills (0–1)
    Uses semantic matching safely (handles tuple returns)
    """

    if not skills:
        return 0.0

    matched = 0

    for skill in skills:
        try:
            result = semantic_match_score(skill, resume_text)

            # semantic_match_score may return float OR tuple
            score = result[0] if isinstance(result, tuple) else result

            if score >= 0.55:
                matched += 1

        except Exception:
            continue

    return matched / len(skills)

# =========================================================
# RESPONSIBILITY MATCH
# =========================================================
def compute_responsibility_match(responsibilities, resume_text):
    """
    Returns ratio of matched responsibilities (0–1)
    """

    if not responsibilities:
        return 0.0

    matched = 0

    for r in responsibilities:
        try:
            result = semantic_match_score(r, resume_text)
            score = result[0] if isinstance(result, tuple) else result

            if score >= 0.50:
                matched += 1

        except Exception:
            continue

    return matched / len(responsibilities)

# =========================================================
# EXPERIENCE ESTIMATION
# =========================================================
def estimate_experience_years(resume_text):

    matches = re.findall(r"(\d+)\+?\s*(?:years|yrs)", resume_text.lower())
    if not matches:
        return 0

    return max(int(x) for x in matches)


def compute_experience_score(required_years, resume_text):

    if not required_years:
        return 1.0

    actual = estimate_experience_years(resume_text)

    if actual >= required_years:
        return 1.0

    return actual / required_years


# =========================================================
# MAIN SCORING ENGINE
# =========================================================
def compute_structured_score(
    resume_text: str,
    job_text: str
) -> Tuple[int, float, Dict]:

    logger.info("Running structured ATS scoring engine...")

    job_structure = extract_job_structure(job_text)

    required_skills = job_structure.get("required_skills", [])
    optional_skills = job_structure.get("optional_skills", [])
    responsibilities = job_structure.get("responsibilities", [])
    min_exp = job_structure.get("min_experience_years", 0)

    required_ratio = compute_skill_coverage(required_skills, resume_text)
    optional_ratio = compute_skill_coverage(optional_skills, resume_text)

    responsibility_ratio = compute_responsibility_match(
        responsibilities,
        resume_text
    )

    experience_ratio = compute_experience_score(
        min_exp,
        resume_text
    )

    resume_emb = get_text_embedding(resume_text)
    job_emb = get_text_embedding(job_text)

    similarity = cosine_similarity(resume_emb, job_emb)

    final_score = (
        required_ratio * REQUIRED_WEIGHT +
        optional_ratio * OPTIONAL_WEIGHT +
        responsibility_ratio * RESPONSIBILITY_WEIGHT +
        experience_ratio * EXPERIENCE_WEIGHT +
        similarity * SEMANTIC_WEIGHT
    )

    percentage = round(final_score * 100, 2)

    logger.info("Final ATS Score: %s", percentage)

    details = {
        "required_coverage": round(required_ratio * 100, 2),
        "optional_coverage": round(optional_ratio * 100, 2),
        "responsibility_match": round(responsibility_ratio * 100, 2),
        "experience_alignment": round(experience_ratio * 100, 2),
        "semantic_similarity": round(similarity * 100, 2),
    }

    return percentage, similarity, details
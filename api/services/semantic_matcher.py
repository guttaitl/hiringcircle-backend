import numpy as np
from api.services.embedding_service import get_text_embedding


def cosine_similarity(vec1, vec2):
    a = np.array(vec1)
    b = np.array(vec2)

    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0

    return float(np.dot(a, b) / denom)


def semantic_match_score(resume_text: str, job_text: str):
    """
    Returns:
        score_percent,
        similarity_raw
    """

    resume_emb = get_text_embedding(resume_text)
    job_emb = get_text_embedding(job_text)

    if not resume_emb or not job_emb:
        return 0.0, 0.0

    similarity = cosine_similarity(resume_emb, job_emb)
    score = round(similarity * 100, 2)

    return score, similarity
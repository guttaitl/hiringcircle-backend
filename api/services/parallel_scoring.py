from concurrent.futures import ThreadPoolExecutor
from api.services.ai_scoring import ai_skill_matrix, ai_overall


def run_parallel(job_title, job_text, resume_text):
    sm = ai_skill_matrix(job_title, job_text, resume_text)
    oa = ai_overall(job_title, job_text, resume_text)
    return sm, oa
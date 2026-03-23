import re

def normalize(text):
    return re.findall(r"[a-z0-9\+#\.]{2,}", (text or "").lower())

def jd_resume_score(jd, resume):
    jd_tokens = set(normalize(jd))
    res_tokens = set(normalize(resume))

    if not jd_tokens:
        return 0

    match = len(jd_tokens & res_tokens)
    return round((match / len(jd_tokens)) * 100)

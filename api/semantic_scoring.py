from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PROMPT = """
You are a technical recruiter scoring a resume against a job description.

Score 0 to 100 based on:
- skills match
- experience relevance
- domain alignment
- responsibilities overlap

Return ONLY a number between 0 and 100.
"""


def semantic_score(jd: str, resume: str) -> int:
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {"role": "system", "content": PROMPT},
                {
                    "role": "user",
                    "content": f"JOB DESCRIPTION:\n{jd}\n\nRESUME:\n{resume}"
                }
            ]
        )

        text = resp.choices[0].message.content.strip()
        score = int("".join(filter(str.isdigit, text)))

        return max(0, min(score, 100))

    except Exception:
        # NEVER FAIL SUBMISSION
        return 0

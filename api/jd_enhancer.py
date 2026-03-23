import os
import time
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def enhance_job_description(title: str, raw_description: str) -> str:

    print("\n----- JD ENHANCER START -----", flush=True)
    print("Title:", title, flush=True)
    print("Raw description length:", len(raw_description or ""), flush=True)

    if not raw_description:
        raw_description = title
        print("Description empty - using title as base", flush=True)

    prompt = f"""
You are an expert technical recruiter.

Expand the following job description into a professional structured format.

Return clean formatted text using sections:

Job Description:
Skills:
Responsibilities:

INPUT:
Job Title: {title}
Details: {raw_description}
"""

    try:
        print("Calling OpenAI...", flush=True)
        start = time.time()

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            timeout=20
        )

        duration = round(time.time() - start, 2)
        print("OpenAI response received in", duration, "seconds", flush=True)

        content = response.choices[0].message.content

        if not content:
            print("OpenAI returned empty content", flush=True)
            return raw_description

        print("Enhanced description length:", len(content), flush=True)
        print("----- JD ENHANCER END -----\n", flush=True)

        return content.strip()

    except Exception as e:
        print("JD enhancement FAILED:", str(e), flush=True)
        print("Returning original description", flush=True)
        print("----- JD ENHANCER END (FAILED) -----\n", flush=True)
        return raw_description

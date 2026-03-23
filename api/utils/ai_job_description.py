from openai import OpenAI
import os
import json
import logging

logger = logging.getLogger(__name__)

# ✅ SAFE CLIENT INIT (NO CRASH)
client = None
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        logger.info("✅ OpenAI client initialized")
    except Exception as e:
        logger.warning(f"⚠️ Failed to init OpenAI client: {e}")
else:
    logger.warning("⚠️ OPENAI_API_KEY missing — AI features disabled")


# ==========================================================
# MAIN GENERATOR
# ==========================================================

def generate_structured_job_content(
    job_title: str,
    experience: str,
    company_name: str = None,
    location: str = None,
    employment_type: str = None,
    industry: str = "Technology"
):
    """
    AI-generated job description.
    Returns None if AI unavailable or fails.
    """

    # 🚨 HARD STOP if no AI
    if not client:
        logger.warning("🚫 AI disabled — skipping generation")
        return None

    location_context = f" in {location}" if location else ""
    employment_context = f" This is a {employment_type} position." if employment_type else ""

    prompt = f"""
You are an expert recruiter.

ROLE: {job_title}
EXPERIENCE: {experience}{location_context}{employment_context}

Return JSON:
{{
  "description": "5-7 line paragraph",
  "required_skills": ["10 real skills"],
  "responsibilities": ["10 real responsibilities"]
}}
"""

    try:
        return _call_ai(prompt)
    except Exception as e:
        logger.error(f"❌ AI generation failed: {e}")
        return None


# ==========================================================
# AI CALL
# ==========================================================

def _call_ai(prompt: str) -> str:
    if not client:
        raise Exception("OpenAI client not initialized")

    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        input=prompt
    )

    text = response.output_text.strip()

    # Extract JSON safely
    start = text.find("{")
    end = text.rfind("}") + 1

    if start == -1 or end == 0:
        raise ValueError("No JSON found in AI response")

    json_text = text[start:end]
    parsed = json.loads(json_text)

    # Validate structure
    for key in ["description", "required_skills", "responsibilities"]:
        if key not in parsed:
            raise ValueError(f"Missing key: {key}")

    parsed["_meta"] = {
        "generated_by": "ai",
        "model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    }

    return json.dumps(parsed, indent=2)


# ==========================================================
# EMAIL FORMATTER
# ==========================================================

def format_for_email(ai_json: str, apply_url: str = "#") -> dict:
    if not ai_json:
        return {
            "job_description": "",
            "skills": "",
            "responsibilities": "",
            "apply_button_html": "",
            "error": "AI unavailable"
        }

    try:
        data = json.loads(ai_json)

        skills = "\n".join([f"• {s}" for s in data.get("required_skills", [])])
        resp = "\n".join([f"• {r}" for r in data.get("responsibilities", [])])

        apply_button_html = f"""
        <div style="margin:20px;text-align:center;">
            <a href="{apply_url}" style="background:#007bff;color:white;padding:12px 24px;text-decoration:none;border-radius:5px;">
                Apply Now
            </a>
        </div>
        """

        return {
            "job_description": data.get("description", ""),
            "skills": skills,
            "responsibilities": resp,
            "apply_button_html": apply_button_html
        }

    except Exception as e:
        logger.error(f"Format error: {e}")
        return {
            "job_description": "",
            "skills": "",
            "responsibilities": "",
            "apply_button_html": "",
            "error": str(e)
        }


# ==========================================================
# LEGACY SUPPORT
# ==========================================================

def generate_job_description(job_title: str, experience: str):
    return generate_structured_job_content(job_title, experience)
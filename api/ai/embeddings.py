from openai import OpenAI
import os
import logging

logger = logging.getLogger(__name__)

client = None
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        logger.info("✅ Embeddings OpenAI client initialized")
    except Exception as e:
        logger.warning(f"⚠️ OpenAI init failed: {e}")
else:
    logger.warning("⚠️ OPENAI_API_KEY missing — embeddings disabled")


def get_embedding(text: str):
    if not client:
        logger.warning("🚫 Embeddings disabled — no API key")
        return None

    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding

    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        return None
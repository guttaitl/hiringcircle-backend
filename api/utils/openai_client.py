"""
OpenAI Client — Production Grade (Key Rotation + Thread Safe)

Features:
- True multi-key rotation (round robin)
- Automatic key switch on 429 / rate limits
- Deterministic retry handling
- Thread safe
- Supports chat + embeddings
- Optional strict JSON parsing
- No fallback models
"""

import os
import time
import json
import threading
import logging
from dotenv import load_dotenv
from openai import OpenAI

logger = logging.getLogger("openai")

# ============================================================
# LOAD ENV (.env + .env.local)
# ============================================================

load_dotenv(".env", override=True)
load_dotenv(".env.local", override=True)

OPENAI_DEBUG = os.getenv("OPENAI_DEBUG", "0") == "1"
MAX_ATTEMPTS = int(os.getenv("OPENAI_MAX_ATTEMPTS", "3"))
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0"))

# ============================================================
# GLOBAL RUNTIME STATE
# ============================================================

_CLIENTS = []
_KEY_INDEX = 0

_INIT_LOCK = threading.Lock()
_CALL_LOCK = threading.Lock()

# ============================================================
# INITIALIZATION
# ============================================================

def _init_openai():
    """
    Initialize all configured OpenAI keys.
    Supports:
    - OPENAI_API_KEYS=key1,key2,key3
    - OPENAI_API_KEY=single_key
    """

    global _CLIENTS

    if _CLIENTS:
        return

    with _INIT_LOCK:
        if _CLIENTS:
            return

        raw = os.getenv("OPENAI_API_KEYS") or os.getenv("OPENAI_API_KEY")

        if not raw:
            raise RuntimeError("OPENAI_API_KEYS not configured")

        keys = [k.strip() for k in raw.split(",") if k.strip()]
        if not keys:
            raise RuntimeError("No valid OpenAI keys found")

        _CLIENTS = [OpenAI(api_key=k) for k in keys]

        logger.info(
            "OpenAI initialized | model=%s | keys_loaded=%s",
            DEFAULT_MODEL,
            len(_CLIENTS)
        )

# ============================================================
# CLIENT ROTATION
# ============================================================

def _next_client():
    """
    Round-robin key rotation.
    Thread safe via CALL_LOCK.
    """
    global _KEY_INDEX

    if not _CLIENTS:
        raise RuntimeError("OpenAI not initialized")

    client = _CLIENTS[_KEY_INDEX]
    _KEY_INDEX = (_KEY_INDEX + 1) % len(_CLIENTS)

    if OPENAI_DEBUG:
        logger.debug("Using OpenAI key index %s", _KEY_INDEX)

    return client

# ============================================================
# SAFE JSON EXTRACTION
# ============================================================

def _extract_json(text: str):
    if not text:
        raise ValueError("Empty OpenAI response")

    text = text.strip()

    # remove markdown blocks if present
    if text.startswith("```"):
        text = text.split("```")[1]

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("No JSON found in AI response")

    return json.loads(text[start:end + 1])

# ============================================================
# CHAT COMPLETION CALL
# ============================================================

def call_openai(
    messages,
    model=None,
    temperature=None,
    expect_json=False
):
    """
    Chat completion with:
    - key rotation
    - retry logic
    - rate-limit auto switch
    """

    _init_openai()

    model = model or DEFAULT_MODEL
    temperature = DEFAULT_TEMPERATURE if temperature is None else temperature

    BACKOFF = [2, 4, 8]
    last_error = None

    with _CALL_LOCK:

        for attempt in range(1, MAX_ATTEMPTS + 1):

            client = _next_client()

            try:
                if OPENAI_DEBUG:
                    logger.debug("OpenAI request attempt %s", attempt)

                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                )

                text = resp.choices[0].message.content

                if expect_json:
                    return _extract_json(text)

                return text

            except Exception as e:
                last_error = e
                err = str(e).lower()

                # Quota exhausted → try next key immediately
                if "insufficient_quota" in err:
                    logger.warning("Quota exhausted on key — switching")
                    continue

                # Rate limit → rotate key immediately
                if "rate" in err or "429" in err:
                    logger.warning("Rate limit hit — switching key")
                    continue

                # Transient issues
                if any(x in err for x in ("timeout", "connection")):
                    if attempt < MAX_ATTEMPTS:
                        time.sleep(BACKOFF[min(attempt - 1, len(BACKOFF) - 1)])
                        continue

                raise

    raise RuntimeError(f"OpenAI failed after retries: {last_error}")

# ============================================================
# EMBEDDING CALL (For Semantic Matching)
# ============================================================

def create_embedding(text: str, model="text-embedding-3-large"):
    """
    Embedding call using same rotation + retry logic.
    Designed for semantic resume-job matching.
    """

    _init_openai()

    if not text:
        return None

    BACKOFF = [2, 4, 8]
    last_error = None

    with _CALL_LOCK:

        for attempt in range(1, MAX_ATTEMPTS + 1):

            client = _next_client()

            try:
                resp = client.embeddings.create(
                    model=model,
                    input=text[:8000]  # truncate safely
                )

                return resp.data[0].embedding

            except Exception as e:
                last_error = e
                err = str(e).lower()

                if "insufficient_quota" in err:
                    logger.warning("Quota exhausted — switching key")
                    continue

                if "rate" in err or "429" in err:
                    logger.warning("Rate limit — switching key")
                    continue

                if any(x in err for x in ("timeout", "connection")):
                    if attempt < MAX_ATTEMPTS:
                        time.sleep(BACKOFF[min(attempt - 1, len(BACKOFF) - 1)])
                        continue

                raise

    raise RuntimeError(f"Embedding failed after retries: {last_error}")

# ============================================================
# OPTIONAL INIT
# ============================================================

def init_openai_keys():
    _init_openai()
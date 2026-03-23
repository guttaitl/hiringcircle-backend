"""
OpenAI Client — Authoritative Mode (100% AI)

Guarantees:
- OpenAI is the ONLY execution path
- No silent fallbacks
- No heuristic degradation
- Hard failure on quota exhaustion
- Bounded retries on rate limits
- Deterministic behavior for worker
"""

import os
import time
import threading
import logging
from dotenv import load_dotenv
from openai import OpenAI

# ============================================================
# LOGGING
# ============================================================
logger = logging.getLogger("openai")

# ============================================================
# LOAD .env (PythonAnywhere + local safe)
# ============================================================
PA_ENV = "/home/hiringcircle/.env"

if os.path.exists(PA_ENV):
    load_dotenv(PA_ENV, override=True)
    logger.info("OpenAI ENV loaded from PythonAnywhere")
else:
    load_dotenv(override=True)
    logger.info("OpenAI ENV loaded from local .env")

# ============================================================
# CONFIG
# ============================================================
OPENAI_DEBUG = os.getenv("OPENAI_DEBUG", "0") == "1"

# IMPORTANT: keep this LOW and predictable
MAX_ATTEMPTS = int(os.getenv("OPENAI_MAX_ATTEMPTS", "2"))

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.0"))

# ============================================================
# RUNTIME STATE (LAZY INIT)
# ============================================================
_OPENAI_KEY = None
_CLIENT = None
_INIT_LOCK = threading.Lock()

# Serialize all OpenAI traffic (TPM-safe)
_OPENAI_CALL_LOCK = threading.Lock()

# ============================================================
# INTERNAL INIT
# ============================================================
def _init_openai():
    """
    Lazy, safe OpenAI initialization.
    Hard-fails if configuration is invalid.
    """
    global _OPENAI_KEY, _CLIENT

    if _CLIENT is not None:
        return

    with _INIT_LOCK:
        if _CLIENT is not None:
            return

        raw = os.getenv("OPENAI_API_KEYS", "").strip()
        if not raw:
            raise RuntimeError("OPENAI_API_KEYS not configured")

        # Org-level limits → pick ONE key only
        _OPENAI_KEY = raw.split(",")[0].strip()
        if not _OPENAI_KEY:
            raise RuntimeError("No valid OpenAI key found")

        _CLIENT = OpenAI(api_key=_OPENAI_KEY)

        logger.info(
            "OpenAI initialized | model=%s | key=****%s",
            DEFAULT_MODEL,
            _OPENAI_KEY[-4:],
        )

# ============================================================
# PUBLIC DIAGNOSTICS
# ============================================================
def get_active_key_info():
    try:
        _init_openai()
        return f"sk-****{_OPENAI_KEY[-4:]}"
    except Exception:
        return "OpenAI not configured"

# ============================================================
# PUBLIC API (AUTHORITATIVE)
# ============================================================
def call_openai(messages, model=None, temperature=None):
    """
    Execute a single authoritative OpenAI request.

    Behavior:
    - Serialized (TPM safe)
    - Retries ONLY on rate limits / transient network errors
    - Immediate failure on quota exhaustion
    - Raises on any unrecoverable error
    """

    _init_openai()

    model = model or DEFAULT_MODEL
    temperature = DEFAULT_TEMPERATURE if temperature is None else temperature

    BACKOFF = [10, 20, 40]  # bounded, predictable
    last_error = None

    with _OPENAI_CALL_LOCK:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                if OPENAI_DEBUG:
                    logger.debug(
                        "OpenAI request | model=%s | attempt=%d",
                        model,
                        attempt,
                    )

                response = _CLIENT.responses.create(
                    model=model,
                    input=messages,
                    temperature=temperature,
                )

                return response

            except Exception as e:
                last_error = e
                err = str(e).lower()

                # ❌ Quota exhaustion → HARD FAIL
                if "insufficient_quota" in err:
                    logger.error("OpenAI quota exhausted")
                    raise

                # ⏳ Rate limits / TPM
                if "rate" in err or "429" in err:
                    if attempt >= MAX_ATTEMPTS:
                        break
                    sleep_for = BACKOFF[min(attempt - 1, len(BACKOFF) - 1)]
                    logger.warning(
                        "⏳ OpenAI rate limit | attempt=%d | sleep=%ss",
                        attempt,
                        sleep_for,
                    )
                    time.sleep(sleep_for)
                    continue

                # 🌐 Transient network issues
                if any(x in err for x in ("timeout", "connection", "tunnel")):
                    if attempt >= MAX_ATTEMPTS:
                        break
                    time.sleep(5)
                    continue

                # ❌ Anything else is fatal
                raise

    raise RuntimeError(f"OpenAI request failed after retries: {last_error}")

# ============================================================
# PUBLIC INIT HOOK
# ============================================================
def init_openai_keys():
    """
    Explicit initializer (optional, safe).
    """
    _init_openai()

from prometheus_client import Counter, Histogram, Gauge


# ==============================
# AI METRICS
# ==============================

AI_CALLS = Counter(
    "ai_calls_total",
    "Total number of OpenAI calls"
)

AI_ERRORS = Counter(
    "ai_errors_total",
    "Total AI failures"
)

AI_LATENCY = Histogram(
    "ai_latency_seconds",
    "Time spent calling OpenAI"
)


# ==============================
# SCORING METRICS
# ==============================

SCORING_STARTED = Counter(
    "scoring_started_total",
    "Scoring jobs started"
)

SCORING_COMPLETED = Counter(
    "scoring_completed_total",
    "Scoring jobs completed"
)

SCORING_FAILED = Counter(
    "scoring_failed_total",
    "Scoring jobs failed"
)


# ==============================
# QUEUE SIZE
# ==============================

QUEUE_SIZE = Gauge(
    "scoring_queue_size",
    "Current number of jobs waiting"
)

from typing import TypedDict


class StartupStats(TypedDict):
    total_resumes: int
    parsed_resumes: int
    embeddings_ready: int
    indexed_resumes: int
    warmup_time_sec: float


startup_stats: StartupStats = {
    "total_resumes": 0,
    "parsed_resumes": 0,
    "embeddings_ready": 0,
    "indexed_resumes": 0,
    "warmup_time_sec": 0.0,   # ← float now
}
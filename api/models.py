from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from datetime import datetime
from typing import Optional
import uuid

Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    job_id: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, default=lambda: str(uuid.uuid4())
    )

    title: Mapped[Optional[str]] = mapped_column(Text)
    company: Mapped[Optional[str]] = mapped_column(Text)
    location: Mapped[Optional[str]] = mapped_column(Text)

    description: Mapped[Optional[str]] = mapped_column(Text)
    requirements: Mapped[Optional[str]] = mapped_column(Text)

    skills: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    submission_id: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, default=lambda: str(uuid.uuid4())
    )

    resume_id: Mapped[Optional[int]] = mapped_column(Integer)

    candidate_name: Mapped[Optional[str]] = mapped_column(Text)

    full_name: Mapped[Optional[str]] = mapped_column(Text)

    resume_text: Mapped[Optional[str]] = mapped_column(Text)

    job_id: Mapped[Optional[str]] = mapped_column(Text)

    job_title: Mapped[Optional[str]] = mapped_column(Text)

    job_description: Mapped[Optional[str]] = mapped_column(Text)

    # AI scoring
    match_score: Mapped[Optional[float]] = mapped_column(Float)

    semantic_similarity: Mapped[Optional[float]] = mapped_column(Float)

    score_breakdown: Mapped[Optional[str]] = mapped_column(Text)

    fit_summary: Mapped[Optional[str]] = mapped_column(Text)

    confidence_band: Mapped[Optional[str]] = mapped_column(String(20))

    final_recommendation: Mapped[Optional[str]] = mapped_column(Text)

    skill_matrix: Mapped[Optional[str]] = mapped_column(Text)

    fabrication_observations: Mapped[Optional[str]] = mapped_column(Text)

    scoring_status: Mapped[Optional[str]] = mapped_column(String(50))

    report_path: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
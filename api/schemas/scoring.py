from pydantic import BaseModel
from typing import List, Literal


Evidence = Literal["EXPLICIT", "IMPLICIT", "PARTIAL", "NO"]


class Skill(BaseModel):
    skill: str
    required: bool
    evidence: Evidence
    reason: str


class SkillMatrix(BaseModel):
    skills: List[Skill]


class OverallFit(BaseModel):
    estimated_years_experience: float
    responsibility_match: float
    domain_match: float
    risk_notes: str
    fitment_summary: str

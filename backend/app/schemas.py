"""Pydantic models shared across agents, gap engine, and API."""
from typing import Literal, Optional

from pydantic import BaseModel, Field

MasteryLevel = Literal["none", "beginner", "intermediate", "advanced"]

MASTERY_SCORE: dict[str, float] = {
    "none": 0.0,
    "beginner": 1.0,
    "intermediate": 2.0,
    "advanced": 3.0,
}


class StudentSkill(BaseModel):
    """A skill the student has, mapped onto the taxonomy."""
    skill_id: str
    name: str
    level: MasteryLevel = "beginner"
    depth_score: int = 1  # 1-10 score for personalization
    evidence: str = ""  # phrase from the student's own text that supports this

class ResumeReviewResult(BaseModel):
    strengths: list[str] = []
    weaknesses: list[str] = []
    formatting_feedback: str = ""
    overall_impression: str = ""



class StudentProfile(BaseModel):
    raw_text: str = ""
    skills: list[StudentSkill] = []
    education: str = ""
    interests: list[str] = []
    hours_per_week: int = 10
    target_role: str = ""


class Subtopic(BaseModel):
    """One curated, ordered sub-topic of a taxonomy skill (skill_subtopics.json)."""
    id: str
    name: str
    level: Literal["beginner", "intermediate", "advanced"]


class SkillDemand(BaseModel):
    """One skill demanded by the market, with evidence from real postings."""
    skill_id: str
    name: str
    frequency: int  # number of postings mentioning it
    share: float  # frequency / postings analysed
    posting_ids: list[str] = []  # evidence trail


class MarketDemandProfile(BaseModel):
    target_role: str
    postings_analysed: int
    skills: list[SkillDemand] = []


class SkillGap(BaseModel):
    skill_id: str
    name: str
    demand_share: float
    current_level: MasteryLevel
    required_level: MasteryLevel
    gap_size: float  # required - current mastery score
    priority: float  # demand_share * gap_size


class GapReport(BaseModel):
    target_role: str
    gaps: list[SkillGap] = []
    strengths: list[str] = []  # demanded skills the student already has


class PathResource(BaseModel):
    course_id: str
    title: str
    provider: str
    url: str
    free: bool = True


class PathStep(BaseModel):
    order: int
    skill_id: str
    skill_name: str
    objective: str
    resources: list[PathResource] = []
    estimated_weeks: float = 1.0
    milestone: str = ""


class RepoChatRequest(BaseModel):
    query: str


class RepoChatResponse(BaseModel):
    answer: str


class LearningPath(BaseModel):
    target_role: str
    steps: list[PathStep] = []
    total_weeks: float = 0.0
    rationale: str = ""


class FGCRCritique(BaseModel):
    """Verifier scores on the FGCR rubric (each 1-5)."""
    feasibility: float = Field(ge=0, le=5)
    groundedness: float = Field(ge=0, le=5)
    coverage: float = Field(ge=0, le=5)
    realism: float = Field(ge=0, le=5)
    passed: bool
    issues: list[str] = []
    revision_request: str = ""

    @property
    def mean_score(self) -> float:
        return (self.feasibility + self.groundedness + self.coverage + self.realism) / 4


class AdvisorResult(BaseModel):
    profile: StudentProfile
    demand: MarketDemandProfile
    gap_report: GapReport
    path: Optional[LearningPath] = None
    critique: Optional[FGCRCritique] = None
    resume_review: Optional[ResumeReviewResult] = None
    revisions_used: int = 0
    notes: list[str] = []


class AdviseRequest(BaseModel):
    resume_text: str
    target_role: str
    hours_per_week: int = 10
    education: str = ""

class JobRecommendation(BaseModel):
    posting_id: str
    title: str
    company: str
    location: str
    url: str = ""
    score: float
    matched_skills: list[str] = []

class InterviewTips(BaseModel):
    role: str
    focus_topics: list[str] = []
    common_questions: list[str] = []
    advice: str = ""


class LeetcodeSummary(BaseModel):
    username: str
    easy: int
    medium: int
    hard: int
    total: int
    dsa_depth: Optional[int] = None
    weak_topics: list[str] = []
    last_accepted_at: Optional[str] = None
    synced_at: Optional[str] = None


class UserCreate(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str


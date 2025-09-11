"""Pydantic models for the interview module."""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class InterviewContext(BaseModel):
    """Context for the interview such as job description."""

    job_description: str
    candidate_resume: Optional[str] = None


class ConversationTurn(BaseModel):
    """A single turn in the interview conversation."""

    role: str
    message: str


class InterviewRequest(BaseModel):
    """Request model for generating the next interview question."""

    context: InterviewContext
    history: List[ConversationTurn] = Field(default_factory=list)
    current_topic: str
    current_difficulty: int
    persona: str = "friendly_mentor"
    needs_hint: bool = False


class InterviewResponse(BaseModel):
    """Response model containing the generated question text."""

    question_text: str


class TopicBlueprint(BaseModel):
    """Details for a single interview topic."""

    name: str
    relevance_to_role: int
    required_depth: str
    jd_context: List[str]
    resume_evidence: List[str]


class InterviewBlueprintResponse(BaseModel):
    """Structured blueprint for an interview session."""

    interview_title: str
    experience_level: str
    topics: List[TopicBlueprint]


class EvaluationRequest(BaseModel):
    """Request model for evaluating a candidate's answer."""

    question: str
    answer: str
    topic_blueprint: TopicBlueprint


class EvaluationResponse(BaseModel):
    """Evaluation details returned by the LLM."""

    score: float
    assessed_depth: str
    llm_confidence: str
    justification: str
    is_truthful: bool


class ProjectContext(BaseModel):
    """Details captured during the warm-up stage about the candidate's project."""

    goal: Optional[str] = None
    constraints: List[str] = Field(default_factory=list)
    scale_latency_slo: Optional[str] = None
    role: Optional[str] = None
    team_size: Optional[str] = None
    architecture: Optional[str] = None
    key_technologies: List[str] = Field(default_factory=list)
    hardest_challenge: Optional[str] = None
    outcomes: Optional[str] = None
    lessons: Optional[str] = None


class VerificationResult(BaseModel):
    """Outcome of a theoretical verification check in Stage-3."""

    skill: str
    result: str
    rationale: Optional[str] = None


class ContextPacket(BaseModel):
    """Shared state passed across interview stages."""

    jd_text: str
    resume_text: str
    duration_min: int = 18
    time_remaining_min: Optional[int] = None
    role_from_jd: Optional[str] = None
    jd_core_skills: List[str] = Field(default_factory=list)
    resume_claims: List[str] = Field(default_factory=list)
    overlap_skills: List[str] = Field(default_factory=list)
    primary_overlap_focus: Optional[str] = None
    selected_project: Optional[str] = None
    project_context: ProjectContext = Field(default_factory=ProjectContext)
    skill_hooks: List[str] = Field(default_factory=list)
    confidence_ratings: Dict[str, int] = Field(default_factory=dict)
    verifications: List[VerificationResult] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)

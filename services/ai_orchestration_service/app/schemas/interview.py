"""Pydantic models for the interview API."""

from typing import List, Optional

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


class InterviewResponse(BaseModel):
    """Response model containing the generated question text."""

    question_text: str


class TopicsResponse(BaseModel):
    """Response model containing inferred interview topics."""

    topics: List[str]

"""API endpoints for interview-related operations."""

from fastapi import APIRouter

from schemas.interview import (
    InterviewRequest,
    InterviewResponse,
    InterviewContext,
    TopicsResponse,
)
from services.llm_service import generate_next_question
from services.topic_service import determine_topics

router = APIRouter()


@router.post("/generate-question", response_model=InterviewResponse)
async def generate_question(request: InterviewRequest) -> InterviewResponse:
    """Generate the next interview question."""

    question = await generate_next_question(request.context, request.history)
    return InterviewResponse(question_text=question)


@router.post("/determine-topics", response_model=TopicsResponse)
async def determine_topics_endpoint(context: InterviewContext) -> TopicsResponse:
    """Determine interview topics based on job description and resume."""

    topics = await determine_topics(context)
    return TopicsResponse(topics=topics)

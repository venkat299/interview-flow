"""API endpoints for interview-related operations."""

from fastapi import APIRouter

from app.schemas.interview import InterviewRequest, InterviewResponse
from app.services.llm_service import generate_next_question

router = APIRouter()


@router.post("/generate-question", response_model=InterviewResponse)
async def generate_question(request: InterviewRequest) -> InterviewResponse:
    """Generate the next interview question."""

    question = await generate_next_question(request.context, request.history)
    return InterviewResponse(question_text=question)

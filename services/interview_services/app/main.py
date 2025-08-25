from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from interview_services.ai_interview_service import (
    generate_next_question,
    determine_topics,
)
from interview_services.schemas import (
    InterviewRequest,
    InterviewResponse,
    InterviewContext,
    TopicsResponse,
)

app = FastAPI(title="Interview Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/generate-question", response_model=InterviewResponse)
async def generate_question(request: InterviewRequest) -> InterviewResponse:
    """Generate the next interview question."""
    question = await generate_next_question(request.context, request.history)
    return InterviewResponse(question_text=question)


@app.post("/determine-topics", response_model=TopicsResponse)
async def determine_topics_endpoint(context: InterviewContext) -> TopicsResponse:
    """Infer interview topics from job description and resume."""
    topics = await determine_topics(context)
    return TopicsResponse(topics=topics)

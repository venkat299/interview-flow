from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ai_orchestration_service.ai_orchestration import (
    generate_next_question,
    determine_topics,
)
from ai_orchestration_service.schemas import (
    InterviewRequest,
    InterviewResponse,
    InterviewContext,
    TopicsResponse,
)

app = FastAPI(title="AI Orchestration Service")

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


# ---- Sample data endpoints (SQLite-backed) ----
from ai_orchestration_service import sample_data_repo as samples


@app.on_event("startup")
def _startup_init_samples() -> None:
    samples.init_db()
    samples.seed_if_empty()


@app.get("/samples")
def list_samples():
    return {"items": samples.list_samples()}


@app.get("/samples/{key}")
def get_sample(key: str):
    item = samples.get_sample(key)
    if not item:
        raise HTTPException(status_code=404, detail="Sample not found")
    return item

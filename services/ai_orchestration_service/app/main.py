from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ai_orchestration_service.ai_orchestration import (
    generate_next_question,
    create_interview_blueprint,
    evaluate_candidate_answer,
)
from ai_orchestration_service.schemas import (
    InterviewRequest,
    InterviewResponse,
    InterviewContext,
    InterviewBlueprintResponse,
    EvaluationRequest,
    EvaluationResponse,
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
    question = await generate_next_question(request)
    return InterviewResponse(question_text=question)


@app.post("/create-blueprint", response_model=InterviewBlueprintResponse)
async def create_blueprint_endpoint(
    context: InterviewContext,
) -> InterviewBlueprintResponse:
    """Create a detailed interview blueprint."""
    return await create_interview_blueprint(context)


@app.post("/evaluate-answer", response_model=EvaluationResponse)
async def evaluate_answer(request: EvaluationRequest) -> EvaluationResponse:
    """Evaluate a candidate's answer to an interview question."""
    return await evaluate_candidate_answer(request)


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

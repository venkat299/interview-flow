from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Initialize logging/tracing as early as possible
from gateway_service.config import settings
from common.logging_config import setup_from_settings

setup_from_settings(settings)

from orchestrator_service.llm_api import (
    generate_next_question,
    create_interview_blueprint,
    on_question_selected,
    on_answer_scored,
    evaluate_candidate_answer,
)
from orchestrator_service.schemas import (
    InterviewRequest,
    InterviewResponse,
    InterviewContext,
    InterviewBlueprintResponse,
    EvaluationRequest,
    EvaluationResponse,
)
from sample_data_service import sample_data_repo as samples
from app_test_service import generate_candidate_for_job
from session_service.service import ConnectionManager as WSConnectionManager
from session_service.database import (
    list_sessions as db_list_sessions,
    get_session as db_get_session,
    get_conversation_turns as db_get_turns,
)
from session_service.report import generate_report_pdf
from fastapi.responses import Response

app = FastAPI(title="API Service")

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


@app.post("/on-question-selected")
async def on_question_selected_endpoint(payload: dict):
    return await on_question_selected(payload.get("question", ""), payload.get("state"))


@app.post("/on-answer-scored")
async def on_answer_scored_endpoint(payload: dict):
    return await on_answer_scored(payload.get("question", ""), payload.get("answer", ""), payload.get("state"))

@app.post("/evaluate-answer", response_model=EvaluationResponse)
async def evaluate_answer(request: EvaluationRequest) -> EvaluationResponse:
    """Evaluate a candidate's answer to an interview question."""
    return await evaluate_candidate_answer(request)


# ---- Sample data endpoints (SQLite-backed) ----


@app.on_event("startup")
def _startup_init_samples() -> None:
    samples.init_db()
    samples.seed_if_empty()

@app.get("/job-postings")
def list_job_postings():
    return {"items": samples.list_job_postings()}


@app.get("/job-postings/{job_id}")
def get_job_posting(job_id: int):
    item = samples.get_job_posting(job_id)
    if not item:
        raise HTTPException(status_code=404, detail="Job not found")
    return item


@app.post("/candidate-resumes")
def upsert_candidate_resume(payload: dict):
    samples.upsert_candidate_resume(
        payload.get("candidate_id"),
        payload.get("resume", ""),
        int(payload.get("job_id")),
    )
    return {"status": "ok"}


@app.get("/candidate-resumes/{candidate_id}")
def get_candidate_resume(candidate_id: str):
    item = samples.get_candidate_resume(candidate_id)
    if not item:
        raise HTTPException(status_code=404, detail="Resume not found")
    return item


@app.post("/app-test/generate-candidate/{job_id}")
async def generate_candidate(job_id: int):
    try:
        return await generate_candidate_for_job(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Job not found")


# ---- Integrated WebSocket + Session retrieval endpoints ----

ws_manager = WSConnectionManager()


@app.websocket("/api/v1/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    await ws_manager.connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_json()
            await ws_manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.get("/api/v1/sessions")
def list_sessions():
    return {"items": db_list_sessions()}


@app.get("/api/v1/sessions/{session_id}")
def get_session(session_id: str):
    sess = db_get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    turns = db_get_turns(session_id)
    return {**sess, "turns": turns}


@app.get("/api/v1/sessions/{session_id}/report")
def download_report(session_id: str):
    sess = db_get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    turns = db_get_turns(session_id)
    pdf_bytes = generate_report_pdf(sess, turns)
    filename = f"interview_report_{session_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

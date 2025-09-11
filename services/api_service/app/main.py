from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from contextlib import asynccontextmanager
import httpx
from fastapi.middleware.cors import CORSMiddleware

# Initialize logging/tracing as early as possible
from gateway_service.config import settings
from gateway_service import gateway as llm_gateway
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
from app_test_service import generate_candidate_for_job, generate_auto_answer_for_session
from session_service.service import ConnectionManager as WSConnectionManager
from session_service.database import (
    list_sessions as db_list_sessions,
    get_session as db_get_session,
    get_conversation_turns as db_get_turns,
)
from session_service.report import generate_report_pdf
from fastapi.responses import Response

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    samples.init_db()
    samples.seed_if_empty()
    # Verify LLM connectivity; abort startup if failing
    await llm_gateway.health_check_active_providers()
    yield
    # Shutdown (nothing to cleanup currently)


app = FastAPI(title="API Service", lifespan=lifespan)

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


# Startup handled in lifespan above

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
    except httpx.TimeoutException:
        # Surface LLM/network timeouts as a 504 to the client
        raise HTTPException(status_code=504, detail="LLM gateway timeout")
    except httpx.HTTPError as e:
        # Other upstream gateway errors
        raise HTTPException(status_code=502, detail=f"LLM gateway error: {str(e)}")


@app.post("/api/v1/sessions/{session_id}/auto-answer")
async def auto_answer(session_id: str, payload: dict):
    """Generate a candidate-style answer to the latest question for the session.

    Body JSON (new preferred):
    - confidence: optional str in {'High','Medium','Low'}
    - verbosity: optional str in {'Concise','Balanced','Verbose'}
    - skill_matrix: optional JSON (array or string)
    - job_description: optional str
    - candidate_resume: optional str
    - candidate_profile: optional str
    - candidate_id: optional str
    - job_id: optional int
    Backwards compatible:
    - correctness_level: float in [0,1]
    - confidence_level: float in [0,1]
    Returns: {"answer_text": str}
    """
    try:
        return await generate_auto_answer_for_session(
            session_id,
            float(payload.get("correctness_level", 0.8)),
            float(payload.get("confidence_level", 0.7)),
            confidence=payload.get("confidence"),
            verbosity=payload.get("verbosity"),
            skill_matrix=payload.get("skill_matrix"),
            job_description=payload.get("job_description"),
            candidate_resume=payload.get("candidate_resume"),
            candidate_profile=payload.get("candidate_profile"),
            candidate_id=payload.get("candidate_id"),
            job_id=payload.get("job_id"),
        )
    except ValueError as e:
        # session not found or no question
        raise HTTPException(status_code=404, detail=str(e))


# ---- Integrated WebSocket + Session retrieval endpoints ----

ws_manager = WSConnectionManager()


@app.websocket("/api/v1/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    await ws_manager.connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_json()
            await ws_manager.handle_message(websocket, data)
            # Break the loop if the connection was closed within the handler
            if websocket.application_state == WebSocketState.DISCONNECTED:
                break
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

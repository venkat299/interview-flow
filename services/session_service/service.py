"""WebSocket session manager using the stage-based orchestrator.

Adds lightweight persistence so REST helpers (e.g., auto-answer)
can retrieve sessions and turns from SQLite.
"""

from typing import Dict, List, Optional

from fastapi import WebSocket
from pydantic import BaseModel, Field

from orchestrator_service import Orchestrator
from orchestrator_service.llm_api import analyze_jd_resume
from .interview_state import InterviewState
from .database import create_session, log_turn


class JoinSessionPayload(BaseModel):
    job_description: str = ""
    candidate_resume: str = ""
    time_limit: Optional[int] = Field(default=None, gt=0)
    word_limit: Optional[int] = Field(default=None, gt=0)


class CandidateAnswerPayload(BaseModel):
    answer: Optional[str] = None
    answer_text: Optional[str] = None

    @property
    def text(self) -> str:
        return self.answer or self.answer_text or ""


class SessionStartedPayload(BaseModel):
    session_id: str


class StageChangedPayload(BaseModel):
    stage: str


class QuestionPayload(BaseModel):
    question_text: str
    stage: str


class TopicStub(BaseModel):
    name: str
    relevance_to_role: int
    required_depth: str
    jd_context: List[str]
    resume_evidence: List[str]


class BlueprintPayload(BaseModel):
    interview_title: str
    experience_level: str
    topics: List[TopicStub]


class ConnectionManager:
    """Minimal connection manager coordinating interview turns."""

    def __init__(self) -> None:
        self.states: Dict[WebSocket, InterviewState] = {}
        self.history: Dict[WebSocket, List[dict]] = {}
        self.orchestrator = Orchestrator()
        # Track session IDs per connection for DB persistence
        self.session_ids: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        await websocket.accept()
        self.session_ids[websocket] = session_id

    def disconnect(self, websocket: WebSocket) -> None:
        self.states.pop(websocket, None)
        self.history.pop(websocket, None)
        self.session_ids.pop(websocket, None)

    async def handle_message(self, websocket: WebSocket, data: dict) -> None:
        event = data.get("event")

        if event == "join_session":
            payload = JoinSessionPayload.model_validate(data.get("payload", {}))

            packet = await analyze_jd_resume(
                payload.job_description,
                payload.candidate_resume,
                duration_min=(payload.time_limit if payload.time_limit else 18),
            )
            state = InterviewState(packet)
            self.states[websocket] = state
            self.history[websocket] = []

            # Persist a session row so REST APIs can find it
            session_id = self.session_ids.get(websocket)
            try:
                create_session(
                    session_id=session_id or "",
                    blueprint=packet.model_dump(),
                    time_limit=payload.time_limit,
                    word_limit=payload.word_limit,
                )
            except Exception:
                # Do not break the session if persistence fails
                pass

            # Inform client the session is live and share a minimal blueprint-like payload
            await websocket.send_json({"event": "session_started", "payload": SessionStartedPayload(session_id=session_id or "").model_dump()})
            # Emit initial stage for UI
            try:
                await websocket.send_json({"event": "stage_changed", "payload": StageChangedPayload(stage=state.current_phase).model_dump()})
            except Exception:
                pass
            # Emit initial ContextPacket for UI
            try:
                await websocket.send_json({"event": "context_packet", "payload": packet.model_dump()})
            except Exception:
                pass
            try:
                # A compact blueprint for the UI (topics inferred from overlap or JD skills)
                topics = (packet.overlap_skills or packet.jd_core_skills or [])
                topic_models = [
                    TopicStub(name=t, relevance_to_role=0, required_depth="", jd_context=[], resume_evidence=[])
                    for t in topics[:7]
                ] or [
                    TopicStub(name="General", relevance_to_role=0, required_depth="", jd_context=[], resume_evidence=[])
                ]
                blueprint_payload = BlueprintPayload(
                    interview_title=packet.role_from_jd or "Interview",
                    experience_level="",
                    topics=topic_models,
                )
                await websocket.send_json({"event": "blueprint", "payload": blueprint_payload.model_dump()})
            except Exception:
                pass

            prev_stage = state.current_phase
            question = await self.orchestrator.loop(state)
            if question:
                self.history[websocket].append({"role": "interviewer", "message": question})
                # If stage advanced during orchestration, inform client
                try:
                    if state.current_phase != prev_stage:
                        await websocket.send_json({"event": "stage_changed", "payload": StageChangedPayload(stage=state.current_phase).model_dump()})
                except Exception:
                    pass
                # Emit updated ContextPacket after orchestration step
                try:
                    await websocket.send_json({"event": "context_packet", "payload": state.packet.model_dump()})
                except Exception:
                    pass
                # Persist interviewer question so auto-answer can find it
                try:
                    if session_id:
                        log_turn(session_id, "interviewer", question)
                except Exception:
                    pass
                await websocket.send_json(
                    {
                        "event": "new_question",
                        "payload": QuestionPayload(question_text=question, stage=state.current_phase).model_dump(),
                    }
                )
            return

        if event in ("candidate_answer", "send_answer"):
            state = self.states.get(websocket)
            if not state:
                return
            payload = CandidateAnswerPayload.model_validate(data.get("payload", {}))
            answer = payload.text
            # Persist candidate answer
            try:
                session_id = self.session_ids.get(websocket)
                if session_id and answer:
                    log_turn(session_id, "candidate", answer)
            except Exception:
                pass
            self.history.setdefault(websocket, []).append({"role": "candidate", "message": answer})
            prev_stage = state.current_phase
            question = await self.orchestrator.loop(state, answer)
            if question is None:
                # If we just transitioned into wrap_up and ended, emit stage_changed once
                try:
                    if prev_stage != "wrap_up":
                        await websocket.send_json({"event": "stage_changed", "payload": StageChangedPayload(stage="wrap_up").model_dump()})
                except Exception:
                    pass
                # Final ContextPacket emission before closing
                try:
                    await websocket.send_json({"event": "context_packet", "payload": state.packet.model_dump()})
                except Exception:
                    pass
                await websocket.send_json({"event": "interview_ended"})
                await websocket.close()
                self.disconnect(websocket)
                return
            self.history[websocket].append({"role": "interviewer", "message": question})
            # If stage advanced during orchestration, inform client
            try:
                if state.current_phase != prev_stage:
                    await websocket.send_json({"event": "stage_changed", "payload": StageChangedPayload(stage=state.current_phase).model_dump()})
            except Exception:
                pass
            # Emit updated ContextPacket after this answer handling
            try:
                await websocket.send_json({"event": "context_packet", "payload": state.packet.model_dump()})
            except Exception:
                pass
            # Persist the next interviewer question
            try:
                session_id = self.session_ids.get(websocket)
                if session_id and question:
                    log_turn(session_id, "interviewer", question)
            except Exception:
                pass
            await websocket.send_json(
                {
                    "event": "new_question",
                    "payload": QuestionPayload(question_text=question, stage=state.current_phase).model_dump(),
                }
            )

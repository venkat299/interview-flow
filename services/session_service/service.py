"""WebSocket session manager using the stage-based orchestrator.

Adds lightweight persistence so REST helpers (e.g., auto-answer)
can retrieve sessions and turns from SQLite.
"""

from typing import Dict, List, Optional

from fastapi import WebSocket

from orchestrator_service import Orchestrator
from orchestrator_service.llm_api import analyze_jd_resume
from .interview_state import InterviewState
from .database import create_session, log_turn


class ConnectionManager:
    """Minimal connection manager coordinating interview turns."""

    def __init__(self) -> None:
        self.states: Dict[WebSocket, InterviewState] = {}
        self.history: Dict[WebSocket, List[dict]] = {}
        self.orchestrator = Orchestrator()
        # Track session IDs per connection for DB persistence
        self.session_ids: Dict[WebSocket, str] = {}
        # Track last question type for logging answers
        self.question_types: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        await websocket.accept()
        self.session_ids[websocket] = session_id

    def disconnect(self, websocket: WebSocket) -> None:
        self.states.pop(websocket, None)
        self.history.pop(websocket, None)
        self.session_ids.pop(websocket, None)
        self.question_types.pop(websocket, None)

    async def handle_message(self, websocket: WebSocket, data: dict) -> None:
        event = data.get("event")

        if event == "join_session":
            payload = data.get("payload", {})
            # Optional runtime limits (minutes/words)
            time_limit: Optional[int] = None
            word_limit: Optional[int] = None
            try:
                if payload.get("time_limit") is not None:
                    time_limit = int(payload.get("time_limit"))
            except Exception:
                time_limit = None
            try:
                if payload.get("word_limit") is not None:
                    word_limit = int(payload.get("word_limit"))
            except Exception:
                word_limit = None

            # Stage-0 analysis builds the context packet
            packet = await analyze_jd_resume(
                payload.get("job_description", ""),
                payload.get("candidate_resume", ""),
                duration_min=(time_limit if isinstance(time_limit, int) and time_limit > 0 else 18),
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
                    time_limit=time_limit,
                    word_limit=word_limit,
                )
            except Exception:
                # Do not break the session if persistence fails
                pass

            # Inform client the session is live and share a minimal blueprint-like payload
            await websocket.send_json({"event": "session_started", "payload": {"session_id": session_id}})
            # Emit initial stage for UI
            try:
                await websocket.send_json({"event": "stage_changed", "payload": {"stage": state.current_phase}})
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
                blueprint_payload = {
                    "interview_title": packet.role_from_jd or "Interview",
                    "experience_level": "",
                    "topics": [{"name": t, "relevance_to_role": 0, "required_depth": "", "jd_context": [], "resume_evidence": []} for t in topics[:7]]
                    or [{"name": "General", "relevance_to_role": 0, "required_depth": "", "jd_context": [], "resume_evidence": []}],
                }
                await websocket.send_json({"event": "blueprint", "payload": blueprint_payload})
            except Exception:
                pass

            prev_stage = state.current_phase
            q_payload = await self.orchestrator.loop(state)
            if q_payload:
                question = q_payload["question_text"]
                qtype = q_payload.get("question_type")
                self.history[websocket].append({"role": "interviewer", "message": question})
                self.question_types[websocket] = qtype or ""
                # If stage advanced during orchestration, inform client
                try:
                    if state.current_phase != prev_stage:
                        await websocket.send_json({"event": "stage_changed", "payload": {"stage": state.current_phase}})
                except Exception:
                    pass
                # Emit updated ContextPacket after orchestration step
                try:
                    await websocket.send_json({"event": "context_packet", "payload": state.packet.model_dump()})
                except Exception:
                    pass
                # Persist interviewer question with metadata
                try:
                    if session_id:
                        log_turn(
                            session_id,
                            "interviewer",
                            question,
                            {"stage": state.current_phase, "question_type": qtype},
                        )
                except Exception:
                    pass
                await websocket.send_json(
                    {
                        "event": "new_question",
                        "payload": {
                            "question_text": question,
                            "stage": state.current_phase,
                            "question_type": qtype,
                        },
                    }
                )
            return

        if event in ("candidate_answer", "send_answer"):
            state = self.states.get(websocket)
            if not state:
                return
            payload = data.get("payload", {})
            # Support both payload shapes
            answer = payload.get("answer") or payload.get("answer_text") or ""
            # Persist candidate answer with metadata
            try:
                session_id = self.session_ids.get(websocket)
                qtype = self.question_types.get(websocket)
                if session_id and answer:
                    log_turn(
                        session_id,
                        "candidate",
                        answer,
                        {"stage": state.current_phase, "question_type": qtype},
                    )
            except Exception:
                pass
            self.history.setdefault(websocket, []).append({"role": "candidate", "message": answer})
            prev_stage = state.current_phase
            q_payload = await self.orchestrator.loop(state, answer)
            if q_payload is None:
                # If we just transitioned into wrap_up and ended, emit stage_changed once
                try:
                    if prev_stage != "wrap_up":
                        await websocket.send_json({"event": "stage_changed", "payload": {"stage": "wrap_up"}})
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
            question = q_payload["question_text"]
            qtype = q_payload.get("question_type")
            self.history[websocket].append({"role": "interviewer", "message": question})
            self.question_types[websocket] = qtype or ""
            # If stage advanced during orchestration, inform client
            try:
                if state.current_phase != prev_stage:
                    await websocket.send_json({"event": "stage_changed", "payload": {"stage": state.current_phase}})
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
                    log_turn(
                        session_id,
                        "interviewer",
                        question,
                        {"stage": state.current_phase, "question_type": qtype},
                    )
            except Exception:
                pass
            await websocket.send_json(
                {
                    "event": "new_question",
                    "payload": {
                        "question_text": question,
                        "stage": state.current_phase,
                        "question_type": qtype,
                    },
                }
            )

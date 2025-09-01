"""Session management for interview WebSocket service."""
from typing import Dict, List

import asyncio
import httpx
from fastapi import WebSocket

from .config import settings
from .schemas import ConversationTurn, InterviewContext
from .interview_state import InterviewState
from .database import create_session, log_turn, end_session


class ConnectionManager:
    """Minimal connection manager for interview sessions."""

    def __init__(self) -> None:
        self.history: Dict[WebSocket, List[dict]] = {}
        self.contexts: Dict[WebSocket, dict] = {}
        self.states: Dict[WebSocket, InterviewState] = {}
        self.session_ids: Dict[WebSocket, str] = {}
        self.ended: Dict[WebSocket, bool] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        await websocket.accept()
        self.history[websocket] = []
        self.session_ids[websocket] = session_id
        self.ended[websocket] = False

    def disconnect(self, websocket: WebSocket) -> None:
        session_id = self.session_ids.get(websocket)
        state = self.states.get(websocket)
        if session_id and not self.ended.get(websocket):
            rubric = {"performance_log": state.performance_log} if state else None
            end_session(session_id, rubric)
        self.history.pop(websocket, None)
        self.contexts.pop(websocket, None)
        self.states.pop(websocket, None)
        self.session_ids.pop(websocket, None)
        self.ended.pop(websocket, None)

    async def handle_message(self, websocket: WebSocket, data: dict) -> None:
        """Process an incoming message from the client."""

        conversation = self.history.setdefault(websocket, [])
        event = data.get("event")
        session_id = self.session_ids.get(websocket)

        if event == "join_session":
            payload = data.get("payload", {})
            context = {
                "job_description": payload.get("job_description", ""),
                "candidate_resume": payload.get("candidate_resume", ""),
            }
            self.contexts[websocket] = context
            blueprint = await self._create_blueprint(context)
            self.states[websocket] = InterviewState(blueprint)
            if session_id:
                create_session(session_id, blueprint)
            await websocket.send_json({"event": "session_started"})
            await websocket.send_json({"event": "blueprint", "payload": blueprint})
            question = await self._next_question(websocket, conversation)
            conversation.append({"role": "interviewer", "message": question})
            if session_id:
                log_turn(session_id, "interviewer", question)
            await websocket.send_json(
                {"event": "new_question", "payload": {"question_text": question}}
            )

        elif event == "send_answer":
            answer = data.get("payload", {}).get("answer_text", "")
            conversation.append({"role": "candidate", "message": answer})
            await websocket.send_json({"event": "interviewer_typing"})
            state = self.states.get(websocket)
            eval_task = self._evaluate_answer(state, conversation)
            question_task = self._next_question(websocket, conversation)
            evaluation_result, question = await asyncio.gather(eval_task, question_task)
            if state:
                state.update_state_after_answer(evaluation_result)
            if session_id:
                log_turn(session_id, "candidate", answer, evaluation_result)
            conversation.append({"role": "interviewer", "message": question})
            if session_id:
                log_turn(session_id, "interviewer", question)
            await websocket.send_json(
                {"event": "new_question", "payload": {"question_text": question}}
            )

        elif event == "end_interview":
            # Persist final rubric/state and close the connection
            state = self.states.get(websocket)
            rubric = {"performance_log": state.performance_log} if state else None
            if session_id:
                end_session(session_id, rubric)
            self.ended[websocket] = True
            await websocket.send_json({"event": "interview_ended"})
            # Close the socket; disconnect handler will run and skip duplicate persist
            await websocket.close()

    async def _next_question(self, websocket: WebSocket, history: List[dict]) -> str:
        context = self.contexts.get(websocket, {"job_description": ""})
        payload = {
            "context": InterviewContext(**context).model_dump(),
            "history": [ConversationTurn(**t).model_dump() for t in history],
        }
        async with httpx.AsyncClient(timeout=settings.ai_timeout) as client:
            resp = await client.post(
                f"{settings.ai_service_url}/generate-question", json=payload
            )
            resp.raise_for_status()
            data = resp.json()
        return data.get("question_text", "")

    async def _create_blueprint(self, context: dict) -> dict:
        payload = InterviewContext(**context).model_dump()
        async with httpx.AsyncClient(timeout=settings.ai_timeout) as client:
            resp = await client.post(
                f"{settings.ai_service_url}/create-blueprint", json=payload
            )
            resp.raise_for_status()
            data = resp.json()
        return data

    async def _evaluate_answer(self, state: InterviewState, history: List[dict]) -> dict:
        payload = {
            "history": [ConversationTurn(**t).model_dump() for t in history],
            "topic": state.current_topic if state else None,
        }
        async with httpx.AsyncClient(timeout=settings.ai_timeout) as client:
            resp = await client.post(
                f"{settings.ai_service_url}/evaluate-answer", json=payload
            )
            resp.raise_for_status()
            data = resp.json()
        return data

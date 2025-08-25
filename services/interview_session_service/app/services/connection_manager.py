"""Manage interview WebSocket sessions."""

import os
import logging
from typing import Dict, List

import httpx
from fastapi import WebSocket


logger = logging.getLogger(__name__)

AI_API_URL = os.getenv("AI_ORCHESTRATION_URL")
USE_DIRECT = os.getenv("AI_ORCHESTRATION_USE_DIRECT", "false").lower() == "true"

if USE_DIRECT:

    try:
        from ai_orchestration_service.app.schemas.interview import (
            ConversationTurn,
            InterviewContext,
        )
        from ai_orchestration_service.app.services.llm_service import (
            generate_next_question as direct_generate_question,
        )
        from ai_orchestration_service.app.services.topic_service import (
            determine_topics as direct_determine_topics,
        )
    except ModuleNotFoundError as exc:
        logger.warning(
            "AI_ORCHESTRATION_USE_DIRECT set but AI orchestration package not found; "
            "falling back to HTTP. Error: %s",
            exc,
        )
        USE_DIRECT = False


class ConnectionManager:
    """Minimal connection manager for interview sessions."""

    def __init__(self) -> None:
        self.history: Dict[WebSocket, List[dict]] = {}
        self.contexts: Dict[WebSocket, dict] = {}

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.history[websocket] = []

    def disconnect(self, websocket: WebSocket) -> None:
        self.history.pop(websocket, None)
        self.contexts.pop(websocket, None)

    async def handle_message(self, websocket: WebSocket, data: dict) -> None:
        """Process an incoming message from the client."""

        logger.info("Received message: %s", data)
        conversation = self.history.setdefault(websocket, [])
        event = data.get("event")

        if event == "join_session":
            payload = data.get("payload", {})
            context = {
                "job_description": payload.get("job_description", ""),
                "candidate_resume": payload.get("candidate_resume", ""),
            }
            self.contexts[websocket] = context
            topics = await self._determine_topics(context)
            await websocket.send_json({"event": "session_started"})
            await websocket.send_json({"event": "topics", "payload": {"topics": topics}})
            question = await self._next_question(websocket, conversation)
            conversation.append({"role": "interviewer", "message": question})
            await websocket.send_json(
                {"event": "new_question", "payload": {"question_text": question}}
            )

        elif event == "send_answer":
            answer = data.get("payload", {}).get("answer_text", "")
            conversation.append({"role": "candidate", "message": answer})
            await websocket.send_json({"event": "interviewer_typing"})
            question = await self._next_question(websocket, conversation)
            conversation.append({"role": "interviewer", "message": question})
            await websocket.send_json(
                {"event": "new_question", "payload": {"question_text": question}}
            )

    async def _next_question(self, websocket: WebSocket, history: List[dict]) -> str:
        context = self.contexts.get(websocket, {"job_description": ""})
        if USE_DIRECT:
            interview_context = InterviewContext(**context)
            turns = [ConversationTurn(**t) for t in history]
            question = await direct_generate_question(interview_context, turns)
            logger.info("Direct generate_question response: %s", question)
            return question
        payload = {"context": context, "history": history}
        logger.info("POST %s/generate-question payload=%s", AI_API_URL, payload)
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{AI_API_URL}/generate-question", json=payload)
            logger.info("Response status %s", getattr(resp, "status_code", "unknown"))
            resp.raise_for_status()
            data = resp.json()
        logger.info("Response body: %s", data)
        return data["question_text"]

    async def _determine_topics(self, context: dict) -> List[str]:
        if USE_DIRECT:
            interview_context = InterviewContext(**context)
            topics = await direct_determine_topics(interview_context)
            logger.info("Direct determine_topics response: %s", topics)
            return topics
        logger.info("POST %s/determine-topics payload=%s", AI_API_URL, context)
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{AI_API_URL}/determine-topics", json=context)
            logger.info("Response status %s", getattr(resp, "status_code", "unknown"))
            resp.raise_for_status()
            data = resp.json()
        logger.info("Response body: %s", data)
        return data.get("topics", [])


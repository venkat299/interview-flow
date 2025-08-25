"""Manage interview WebSocket sessions."""

import os
from typing import Dict, List

import httpx
from fastapi import WebSocket


AI_API_URL = os.getenv("AI_ORCHESTRATION_URL")


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
        payload = {"context": context, "history": history}
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{AI_API_URL}/generate-question", json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data["question_text"]

    async def _determine_topics(self, context: dict) -> None:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{AI_API_URL}/determine-topics", json=context)
            resp.raise_for_status()
            return resp.json().get("topics", [])


"""Manage interview WebSocket sessions."""

import os
from typing import Dict, List

import httpx
from fastapi import WebSocket


AI_API_URL = os.getenv(
    "AI_ORCHESTRATION_URL", "http://localhost:8001/api/v1/interview"
)


class ConnectionManager:
    """Minimal connection manager for interview sessions."""

    def __init__(self) -> None:
        self.history: Dict[WebSocket, List[dict]] = {}

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.history[websocket] = []

    def disconnect(self, websocket: WebSocket) -> None:
        self.history.pop(websocket, None)

    async def handle_message(self, websocket: WebSocket, data: dict) -> None:
        """Process an incoming message from the client."""

        conversation = self.history.setdefault(websocket, [])
        event = data.get("event")

        if event == "join_session":
            await websocket.send_json({"event": "session_started"})
            question = await self._next_question(conversation)
            conversation.append({"role": "interviewer", "message": question})
            await websocket.send_json(
                {"event": "new_question", "payload": {"question_text": question}}
            )

        elif event == "send_answer":
            answer = data.get("payload", {}).get("answer_text", "")
            conversation.append({"role": "candidate", "message": answer})
            await websocket.send_json({"event": "interviewer_typing"})
            question = await self._next_question(conversation)
            conversation.append({"role": "interviewer", "message": question})
            await websocket.send_json(
                {"event": "new_question", "payload": {"question_text": question}}
            )

    async def _next_question(self, history: List[dict]) -> str:
        payload = {
            "context": {"job_description": "Backend developer"},
            "history": history,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{AI_API_URL}/generate-question", json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data["question_text"]


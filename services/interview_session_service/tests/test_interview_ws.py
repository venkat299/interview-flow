import sys
from pathlib import Path
import importlib.util
import httpx
from httpx import Response, Request
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

ROOT = Path(__file__).resolve().parents[3]
SESSION_APP_PATH = ROOT / "services/interview_session_service/app"
sys.path.insert(0, str(SESSION_APP_PATH))
sys.path.append(str(ROOT))

spec_cm = importlib.util.spec_from_file_location("services.connection_manager", SESSION_APP_PATH / "services/connection_manager.py")
connection_manager = importlib.util.module_from_spec(spec_cm)
sys.modules["services.connection_manager"] = connection_manager
spec_cm.loader.exec_module(connection_manager)

spec_ws = importlib.util.spec_from_file_location("interview_ws", SESSION_APP_PATH / "api/v1/endpoints/interview_ws.py")
interview_ws = importlib.util.module_from_spec(spec_ws)
spec_ws.loader.exec_module(interview_ws)

session_app = FastAPI()
session_app.include_router(interview_ws.router, prefix="/api/v1")


@pytest.fixture(autouse=True)
def patch_ai_url(monkeypatch):
    monkeypatch.setattr(connection_manager, "AI_API_URL", "http://ai/interview")


class DummyResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data

    def raise_for_status(self):
        pass


@pytest.mark.asyncio
async def test_join_session_sends_first_question(monkeypatch):
    async def fake_post(self, url, json=None):
        if url.endswith("/determine-topics"):
            return DummyResponse({"topics": ["python"]})
        assert url == "http://ai/interview/generate-question"
        return DummyResponse({"question_text": "First question?"})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with TestClient(session_app) as client:
        with client.websocket_connect("/api/v1/ws/test") as websocket:
            websocket.send_json({
                "event": "join_session",
                "payload": {
                    "interview_id": "test",
                    "job_description": "Backend dev",
                    "candidate_resume": "Experienced in Python",
                },
            })
            data1 = websocket.receive_json()
            data2 = websocket.receive_json()
            data3 = websocket.receive_json()

    assert data1 == {"event": "session_started"}
    assert data2 == {"event": "topics", "payload": {"topics": ["python"]}}
    assert data3 == {"event": "new_question", "payload": {"question_text": "First question?"}}


@pytest.mark.asyncio
async def test_send_answer_triggers_followup(monkeypatch):
    questions = iter(["First question?", "Second question?"])

    async def fake_post(self, url, json=None):
        if url.endswith("/determine-topics"):
            return DummyResponse({"topics": ["python"]})
        return DummyResponse({"question_text": next(questions)})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with TestClient(session_app) as client:
        with client.websocket_connect("/api/v1/ws/test") as websocket:
            websocket.send_json({
                "event": "join_session",
                "payload": {
                    "interview_id": "test",
                    "job_description": "Backend dev",
                    "candidate_resume": "Experienced in Python",
                },
            })
            websocket.receive_json()  # session_started
            websocket.receive_json()  # topics
            websocket.receive_json()  # first question

            websocket.send_json({"event": "send_answer", "payload": {"answer_text": "hi"}})
            typing_event = websocket.receive_json()
            followup_event = websocket.receive_json()

    assert typing_event == {"event": "interviewer_typing"}
    assert followup_event == {
        "event": "new_question",
        "payload": {"question_text": "Second question?"},
    }

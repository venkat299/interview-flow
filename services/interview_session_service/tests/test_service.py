import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import pytest
import asyncio

from interview_session_service import service as session


class DummyWebSocket:
    def __init__(self):
        self.sent = []

    async def accept(self):
        pass

    async def send_json(self, data):
        self.sent.append(data)


@pytest.mark.asyncio
async def test_join_session_sends_first_question(monkeypatch):
    async def fake_question(self, websocket, history):
        return "First question?"

    async def fake_blueprint(self, context):
        return {
            "topics": [
                {
                    "name": "python",
                    "relevance_to_role": 1,
                    "required_depth": "Fundamental",
                    "jd_context": [],
                    "resume_evidence": [],
                }
            ]
        }

    monkeypatch.setattr(session.ConnectionManager, "_next_question", fake_question)
    monkeypatch.setattr(session.ConnectionManager, "_create_blueprint", fake_blueprint)
    monkeypatch.setattr(session, "create_session", lambda *a, **k: None)
    monkeypatch.setattr(session, "log_turn", lambda *a, **k: None)
    monkeypatch.setattr(session, "end_session", lambda *a, **k: None)

    ws = DummyWebSocket()
    manager = session.ConnectionManager()
    await manager.connect(ws, "session-test")
    await manager.handle_message(
        ws,
        {
            "event": "join_session",
            "payload": {
                "job_description": "Backend dev",
                "candidate_resume": "Experienced in Python",
            },
        },
    )

    assert ws.sent[0] == {"event": "session_started"}
    assert ws.sent[1] == {
        "event": "blueprint",
        "payload": {
            "topics": [
                {
                    "name": "python",
                    "relevance_to_role": 1,
                    "required_depth": "Fundamental",
                    "jd_context": [],
                    "resume_evidence": [],
                }
            ]
        },
    }
    assert ws.sent[2] == {
        "event": "new_question",
        "payload": {"question_text": "First question?"},
    }


@pytest.mark.asyncio
async def test_send_answer_triggers_followup(monkeypatch):
    questions = iter(["First question?", "Second question?"])

    async def fake_question(self, websocket, history):
        await asyncio.sleep(0.1)
        return next(questions)

    async def fake_evaluate(self, state, history):
        await asyncio.sleep(0.1)
        return {"score": 5}

    async def fake_blueprint(self, context):
        return {
            "topics": [
                {
                    "name": "python",
                    "relevance_to_role": 1,
                    "required_depth": "Fundamental",
                    "jd_context": [],
                    "resume_evidence": [],
                }
            ]
        }

    monkeypatch.setattr(session.ConnectionManager, "_next_question", fake_question)
    monkeypatch.setattr(session.ConnectionManager, "_evaluate_answer", fake_evaluate)
    monkeypatch.setattr(session.ConnectionManager, "_create_blueprint", fake_blueprint)
    monkeypatch.setattr(session, "create_session", lambda *a, **k: None)
    monkeypatch.setattr(session, "log_turn", lambda *a, **k: None)
    monkeypatch.setattr(session, "end_session", lambda *a, **k: None)

    ws = DummyWebSocket()
    manager = session.ConnectionManager()
    await manager.connect(ws, "session-test")
    await manager.handle_message(
        ws,
        {
            "event": "join_session",
            "payload": {
                "job_description": "Backend dev",
                "candidate_resume": "Experienced in Python",
            },
        },
    )

    ws.sent.clear()
    start = asyncio.get_event_loop().time()
    await manager.handle_message(
        ws, {"event": "send_answer", "payload": {"answer_text": "hi"}}
    )
    duration = asyncio.get_event_loop().time() - start

    assert ws.sent[0] == {"event": "interviewer_typing"}
    assert ws.sent[1] == {
        "event": "new_question",
        "payload": {"question_text": "Second question?"},
    }
    assert duration < 0.2

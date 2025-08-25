import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import pytest

from interview_services import interview_session_service as session


class DummyWebSocket:
    def __init__(self):
        self.sent = []

    async def accept(self):
        pass

    async def send_json(self, data):
        self.sent.append(data)


@pytest.mark.asyncio
async def test_join_session_sends_first_question(monkeypatch):
    async def fake_question(context, turns):
        return "First question?"

    async def fake_topics(context):
        return ["python"]

    monkeypatch.setattr(session, "generate_next_question", fake_question)
    monkeypatch.setattr(session, "determine_topics", fake_topics)

    ws = DummyWebSocket()
    manager = session.ConnectionManager()
    await manager.connect(ws)
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
    assert ws.sent[1] == {"event": "topics", "payload": {"topics": ["python"]}}
    assert ws.sent[2] == {
        "event": "new_question",
        "payload": {"question_text": "First question?"},
    }


@pytest.mark.asyncio
async def test_send_answer_triggers_followup(monkeypatch):
    questions = iter(["First question?", "Second question?"])

    async def fake_question(context, turns):
        return next(questions)

    async def fake_topics(context):
        return ["python"]

    monkeypatch.setattr(session, "generate_next_question", fake_question)
    monkeypatch.setattr(session, "determine_topics", fake_topics)

    ws = DummyWebSocket()
    manager = session.ConnectionManager()
    await manager.connect(ws)
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
    await manager.handle_message(
        ws, {"event": "send_answer", "payload": {"answer_text": "hi"}}
    )

    assert ws.sent[0] == {"event": "interviewer_typing"}
    assert ws.sent[1] == {
        "event": "new_question",
        "payload": {"question_text": "Second question?"},
    }

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient

from api_service.app.main import app
from gateway_service import gateway


@pytest.fixture
def client():
    return TestClient(app)


def test_generate_question_endpoint(monkeypatch, client):
    async def fake_execute(task_name, system_prompt, user_prompt=None):
        assert task_name == "question_generation"
        return {"question_text": "Sample?"}

    monkeypatch.setattr(gateway, "execute_task", fake_execute)

    payload = {
        "context": {"job_description": "Backend developer"},
        "history": [{"role": "candidate", "message": "Hi"}],
        "current_topic": "python",
        "current_difficulty": 2,
        "persona": "friendly_mentor",
    }
    resp = client.post("/generate-question", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"question_text": "Sample?"}


def test_create_blueprint_endpoint(monkeypatch, client):
    async def fake_execute(task_name, system_prompt, user_prompt=None):
        return {
            "interview_title": "Backend Developer Interview",
            "experience_level": "Senior",
            "topics": [],
        }

    monkeypatch.setattr(gateway, "execute_task", fake_execute)

    payload = {
        "job_description": "Looking for Python developer",
        "candidate_resume": "Experience with databases",
    }
    resp = client.post("/create-blueprint", json=payload)
    assert resp.status_code == 200
    assert resp.json()["interview_title"] == "Backend Developer Interview"


def test_evaluate_answer_endpoint(monkeypatch, client):
    async def fake_execute(task_name, system_prompt, user_prompt=None):
        assert task_name == "answer_evaluation"
        return {
            "score": 9,
            "assessed_depth": "Advanced",
            "llm_confidence": "High",
            "justification": "Great",
            "is_truthful": True,
        }

    monkeypatch.setattr(gateway, "execute_task", fake_execute)

    payload = {
        "question": "What is Python?",
        "answer": "A programming language",
        "topic_blueprint": {
            "name": "python",
            "relevance_to_role": 10,
            "required_depth": "Advanced",
            "jd_context": ["python"],
            "resume_evidence": ["python"],
        },
    }
    resp = client.post("/evaluate-answer", json=payload)
    assert resp.status_code == 200
    assert resp.json()["score"] == 9

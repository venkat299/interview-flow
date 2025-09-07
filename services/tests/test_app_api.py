import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient

from api_service.app.main import app
from gateway_service import gateway


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


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


def test_job_postings_and_resumes(client):
    resp = client.get("/job-postings")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert any(it["id"] == 1 for it in items)

    resp = client.get("/job-postings/1")
    assert resp.status_code == 200
    assert resp.json()["job_title"] == "Junior Frontend Developer"

    resume_payload = {
        "candidate_id": "cand1",
        "resume": "Skilled developer",
        "job_id": 1,
    }
    resp = client.post("/candidate-resumes", json=resume_payload)
    assert resp.status_code == 200

    resp = client.get("/candidate-resumes/cand1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["job_id"] == 1


def test_app_test_generate_candidate(monkeypatch, client):
    async def fake_execute(task_name, system_prompt, user_prompt=None):
        return {"resume": "Generated resume"}

    monkeypatch.setattr(gateway, "execute_task", fake_execute)

    resp = client.post("/app-test/generate-candidate/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["resume"] == "Generated resume"
    assert data["candidate_id"]

    # Verify resume stored
    resp = client.get(f"/candidate-resumes/{data['candidate_id']}")
    assert resp.status_code == 200
    stored = resp.json()
    assert stored["resume"] == "Generated resume" and stored["job_id"] == 1

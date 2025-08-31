import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import httpx
import pytest
from fastapi.testclient import TestClient

from ai_orchestration_service.app.main import app
from ai_orchestration_service.config import settings
from ai_orchestration_service.ai_gateway import gateway


@pytest.fixture
def client():
    return TestClient(app)


def test_generate_question_endpoint(monkeypatch, client):
    settings.llm_provider = "openai"

    async def fake_post(self, url, headers=None, json=None):
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Sample?"}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    payload = {
        "context": {"job_description": "Backend developer"},
        "history": [{"role": "candidate", "message": "Hi"}],
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

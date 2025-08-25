import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import httpx
import pytest
from fastapi.testclient import TestClient

from interview_services.app.main import app
from interview_services.config import settings


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


def test_determine_topics_endpoint(client):
    payload = {
        "job_description": "Looking for Python developer",
        "candidate_resume": "Experience with databases",
    }
    resp = client.post("/determine-topics", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"topics": ["python", "database"]}

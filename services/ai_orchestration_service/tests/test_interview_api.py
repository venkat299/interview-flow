import sys
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "app"))

from core.config import settings
from main import app


@pytest.mark.asyncio
async def test_generate_question(monkeypatch):
    original_post = httpx.AsyncClient.post

    async def fake_post(self, url, headers=None, json=None):
        if url == "https://api.openai.com/v1/chat/completions":
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": "What is your experience with Python?"}}
                    ]
                },
                request=httpx.Request("POST", url),
            )
        return await original_post(self, url, headers=headers, json=json)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    # Ensure the service is using the OpenAI provider for this test
    settings.llm_provider = "openai"

    payload = {
        "context": {"job_description": "Backend developer"},
        "history": [{"role": "candidate", "message": "Hi"}],
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/interview/generate-question", json=payload
        )

    assert response.status_code == 200
    assert response.json() == {
        "question_text": "What is your experience with Python?"
    }


@pytest.mark.asyncio
async def test_determine_topics():
    payload = {
        "job_description": "Looking for Python developer",
        "candidate_resume": "Experience with databases",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/interview/determine-topics", json=payload
        )

    assert response.status_code == 200
    assert response.json() == {"topics": ["python", "database"]}

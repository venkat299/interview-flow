import sys
from pathlib import Path

import httpx
import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "app"))

from core.config import settings
from schemas.interview import InterviewContext, ConversationTurn
from services.llm_service import generate_next_question


@pytest.mark.asyncio
async def test_generate_next_question_uses_configured_timeout(monkeypatch):
    settings.llm_provider = "openai"
    settings.llm_timeout = 7.5

    captured = {}

    class DummyClient:
        def __init__(self, *args, **kwargs):
            captured["timeout"] = kwargs.get("timeout")

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def post(self, url, headers=None, json=None):
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "Example?"}}]},
                request=httpx.Request("POST", url),
            )

    monkeypatch.setattr(httpx, "AsyncClient", DummyClient)

    await generate_next_question(
        InterviewContext(job_description="Backend developer"),
        [ConversationTurn(role="candidate", message="Hi")],
    )

    assert captured["timeout"] == settings.llm_timeout

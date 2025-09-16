import sys
import asyncio
import types
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

if "yaml" not in sys.modules:
    sys.modules["yaml"] = types.SimpleNamespace(safe_load=lambda *_args, **_kwargs: {})

if "httpx" not in sys.modules:
    class _DummyAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def post(self, *args, **kwargs):  # pragma: no cover - network stub
            raise RuntimeError("httpx is not installed")

    class _DummyTimeout:
        def __init__(self, *args, **kwargs):
            pass

    sys.modules["httpx"] = types.SimpleNamespace(
        AsyncClient=_DummyAsyncClient,
        Timeout=_DummyTimeout,
    )

if "json_repair" not in sys.modules:
    sys.modules["json_repair"] = types.SimpleNamespace(repair_json=lambda text: text)

from app_test_service import service as auto_service


def test_generate_auto_answer_uses_dedicated_task(monkeypatch):
    """Auto-answer requests should be routed through the dedicated provider."""

    monkeypatch.setattr(
        auto_service,
        "db_get_session",
        lambda session_id: {"blueprint": {"topics": []}},
    )

    monkeypatch.setattr(
        auto_service,
        "db_get_turns",
        lambda session_id: [
            {"role": "interviewer", "message": "What is your experience with Python?"}
        ],
    )

    captured = {}

    async def fake_execute(task_name, system_prompt, user_prompt=None):
        captured["task_name"] = task_name
        return {"answer_text": "Mock answer"}

    monkeypatch.setattr(auto_service.gateway, "execute_task", fake_execute)

    result = asyncio.run(
        auto_service.generate_auto_answer_for_session("sess-123", 0.0, 0.5)
    )

    assert result["answer_text"] == "Mock answer"
    assert captured["task_name"] == "auto_answer_generation"

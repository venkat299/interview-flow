import pytest
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from orchestrator_service import llm_api
from orchestrator_service.schemas import ContextPacket


@pytest.mark.asyncio
async def test_warmup_role_skips_when_role_present(monkeypatch):
    packet = ContextPacket(jd_text="jd", resume_text="resume")
    packet.project_context.role = "Developer"

    async def fake_execute(*args, **kwargs):
        raise AssertionError("execute_task should not be called")

    monkeypatch.setattr(llm_api.gateway, "execute_task", fake_execute)

    result = await llm_api.warmup_role(packet)
    assert result is None


@pytest.mark.asyncio
async def test_evidence_choice_space_skips_when_note_present(monkeypatch):
    packet = ContextPacket(jd_text="jd", resume_text="resume")
    packet.notes.append("Choice space: done")

    async def fake_execute(*args, **kwargs):
        raise AssertionError("execute_task should not be called")

    monkeypatch.setattr(llm_api.gateway, "execute_task", fake_execute)

    result = await llm_api.evidence_choice_space(packet)
    assert result is None

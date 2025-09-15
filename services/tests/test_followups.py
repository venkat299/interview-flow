import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest

from orchestrator_service import llm_api as ai
from orchestrator_service.orchestrator import Orchestrator
from session_service.interview_state import InterviewState
from orchestrator_service.schemas import ContextPacket
import orchestrator_service.orchestrator as orch_mod


@pytest.mark.asyncio
async def test_followup_injection(monkeypatch):
    packet = ContextPacket(jd_text="JD", resume_text="Resume", followup_hooks=["kafka", "kubernetes"])
    state = InterviewState(packet)
    orch = Orchestrator()

    async def fake_primary(packet, skill, answer=None):
        return {"question_text": "primary", "question_type": "theory_primary"}

    async def fake_followup(packet, skill, answer=None):
        return None

    monkeypatch.setattr(orch_mod, "theory_primary_question", fake_primary)
    monkeypatch.setattr(orch_mod, "theory_followup_question", fake_followup)

    q1 = await orch.loop(state)
    assert q1["question_type"] == "targeted_followup"
    q2 = await orch.loop(state, "details1")
    assert q2["question_type"] == "targeted_followup"
    q3 = await orch.loop(state, "details2")
    assert q3["question_type"] == "theory_primary"


@pytest.mark.asyncio
async def test_theory_eval_handles_bad_json(monkeypatch):
    async def fake_eval(inp):
        raise ValueError("bad json")

    monkeypatch.setattr(ai, "_theory_eval", fake_eval)

    packet = ContextPacket(jd_text="JD", resume_text="Resume")

    await ai.theory_primary_question(packet, "kafka", answer="ans")
    ver = packet.verifications[-1]
    assert ver.result == "fail"
    assert "bad json" in ver.rationale

    await ai.theory_followup_question(packet, "kafka", answer="ans2")
    ver = packet.verifications[-1]
    assert ver.followup_result == "fail"
    assert "bad json" in ver.followup_rationale

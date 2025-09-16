import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest

from orchestrator_service.orchestrator import Orchestrator
from session_service.interview_state import InterviewState
from orchestrator_service.schemas import ContextPacket


@pytest.mark.asyncio
async def test_followup_injection():
    packet = ContextPacket(jd_text="JD", resume_text="Resume", followup_hooks=["kafka", "kubernetes"])
    state = InterviewState(packet)
    orch = Orchestrator()

    q1 = await orch.loop(state)
    assert q1["question_type"] == "targeted_followup"
    q2 = await orch.loop(state, "details1")
    assert q2["question_type"] == "targeted_followup"
    q3 = await orch.loop(state, "details2")
    assert q3["question_type"] == "intro_greeting"

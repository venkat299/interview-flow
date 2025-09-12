import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from orchestrator_service import llm_api as ai
from orchestrator_service.orchestrator import Orchestrator
from session_service.interview_state import InterviewState
from orchestrator_service.schemas import ContextPacket


@pytest.mark.asyncio
async def test_keyword_followup_injected(monkeypatch):
    qgen_iter = iter([
        {"question_text": "project?"},
        {"question_text": "role?"},
        {"question_text": "architecture?"},
        {"question_text": "constraints?"},
    ])
    parse_iter = iter([
        {"project_name": "demo"},
        {"role": "lead", "team_size": "5"},
        {"architecture": "svc", "key_technologies": ["python"], "followup_hooks": []},
    ])

    async def fake_execute(task_name, system_prompt, user_prompt=None):
        if task_name == "stage_0_analysis":
            return {
                "role_from_jd": "backend",
                "jd_core_skills": [],
                "resume_claims": [],
                "overlap_skills": [],
                "primary_overlap_focus": "backend",
            }
        if task_name == "skill_tag_refinement":
            return {"tags": []}
        if task_name == "question_generation":
            return next(qgen_iter)
        if task_name == "stage_1_parse":
            return next(parse_iter)
        raise AssertionError(task_name)

    monkeypatch.setattr(ai.gateway, "execute_task", fake_execute)

    packet = await ai.analyze_jd_resume("JD", "Resume")
    state = InterviewState(packet)
    orch = Orchestrator()

    q1 = await orch.loop(state)
    assert q1["question_type"] == "warmup_project"

    q2 = await orch.loop(state, "demo project")
    assert q2["question_type"] == "warmup_role"

    q3 = await orch.loop(state, "lead of 5")
    assert q3["question_type"] == "warmup_architecture"

    q4 = await orch.loop(state, "svc using Kafka")
    assert q4["question_type"] == "targeted_followup"
    assert "Kafka" in q4["question_text"]

    q5 = await orch.loop(state, "details about kafka on Kubernetes")
    assert q5["question_type"] == "targeted_followup"
    assert "Kubernetes" in q5["question_text"]

    q6 = await orch.loop(state, "k8s follow-up response")
    assert q6["question_type"] == "warmup_constraints"


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

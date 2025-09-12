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
            return {"question_text": "q"}
        if task_name == "stage_1_parse":
            if "project name" in system_prompt:
                return {"project_name": "demo"}
            if "goal" in system_prompt:
                return {"goal": "demo", "constraints": []}
            if "role and team_size" in system_prompt:
                if "lead" in (user_prompt or "").lower():
                    return {"role": "lead", "team_size": None}
                if "5" in (user_prompt or ""):
                    return {"role": None, "team_size": "5"}
            if "architecture" in system_prompt:
                if "svc" in (user_prompt or ""):
                    return {"architecture": "svc", "key_technologies": [], "followup_hooks": []}
                return {"architecture": None, "key_technologies": [], "followup_hooks": []}
            if "constraints" in system_prompt and "list" in system_prompt:
                return {"constraints": ["latency"]}
        raise AssertionError(task_name)

    monkeypatch.setattr(ai.gateway, "execute_task", fake_execute)

    packet = await ai.analyze_jd_resume("JD", "Resume")
    state = InterviewState(packet)
    orch = Orchestrator()

    q1 = await orch.loop(state)
    assert q1["question_type"] == "warmup_project"

    q2 = await orch.loop(state, "demo project")
    assert q2["question_type"] == "warmup_project_overview"

    q3 = await orch.loop(state, "overview")
    assert q3["question_type"] == "warmup_role"

    q4 = await orch.loop(state, "lead")
    assert q4["question_type"] == "warmup_team_size"

    q5 = await orch.loop(state, "5")
    assert q5["question_type"] == "warmup_architecture"

    q6 = await orch.loop(state, "svc")
    assert q6["question_type"] == "warmup_tech_stack"

    q7 = await orch.loop(state, "Kafka")
    assert q7["question_type"] == "targeted_followup"
    assert "kafka" in q7["question_text"].lower()

    q8 = await orch.loop(
        state,
        "We streamed events using Kafka brokers and scheduled them via Kubernetes controllers",
    )
    assert q8["question_type"] == "targeted_followup"
    assert "kubernetes" in q8["question_text"].lower()

    q9 = await orch.loop(
        state,
        "Our Kubernetes deployment handled scaling, monitoring, and updates without downtime",
    )
    assert q9["question_type"] == "warmup_constraints"
    assert state.packet.resolved_followup_hooks == ["kafka", "kubernetes"]


@pytest.mark.asyncio
async def test_followup_skipped_when_explained(monkeypatch):
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
            return {"question_text": "q"}
        if task_name == "stage_1_parse":
            if "project name" in system_prompt:
                return {"project_name": "demo"}
            if "goal" in system_prompt:
                return {"goal": "demo", "constraints": []}
            if "role and team_size" in system_prompt:
                if "lead" in (user_prompt or "").lower():
                    return {"role": "lead", "team_size": None}
                if "5" in (user_prompt or ""):
                    return {"role": None, "team_size": "5"}
            if "architecture" in system_prompt:
                if "svc" in (user_prompt or ""):
                    return {"architecture": "svc", "key_technologies": [], "followup_hooks": []}
                return {"architecture": None, "key_technologies": [], "followup_hooks": []}
            if "constraints" in system_prompt and "list" in system_prompt:
                return {"constraints": ["latency"]}
        raise AssertionError(task_name)

    monkeypatch.setattr(ai.gateway, "execute_task", fake_execute)

    packet = await ai.analyze_jd_resume("JD", "Resume")
    state = InterviewState(packet)
    orch = Orchestrator()

    await orch.loop(state)
    await orch.loop(state, "demo project")
    await orch.loop(state, "overview")
    await orch.loop(state, "lead")
    await orch.loop(state, "5")
    await orch.loop(state, "svc")

    q7 = await orch.loop(state, "Kafka")
    assert q7["question_type"] == "targeted_followup"

    q8 = await orch.loop(
        state,
        "We used Kafka and Kubernetes to orchestrate microservices and manage scaling efficiently",
    )
    assert q8["question_type"] == "warmup_constraints"
    assert state.packet.resolved_followup_hooks == ["kafka", "kubernetes"]


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


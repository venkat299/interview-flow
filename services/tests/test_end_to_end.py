import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest

from orchestrator_service import llm_api as ai
from orchestrator_service.schemas import ContextPacket, ProjectContext
from orchestrator_service.orchestrator import Orchestrator
from session_service.interview_state import InterviewState


@pytest.mark.asyncio
async def test_run_interview_end_to_end(monkeypatch):
    async def fake_execute(task_name, system_prompt, user_prompt=None):
        if task_name == "stage_0_analysis":
            return {
                "role_from_jd": "backend",
                "jd_core_skills": ["python"],
                "resume_claims": ["python"],
                "overlap_skills": ["python"],
                "primary_overlap_focus": "python",
            }
        if task_name == "skill_tag_refinement":
            return {"tags": []}
        if task_name == "stage_1_parse":
            if "project name" in system_prompt:
                return {"project_name": "demo"}
            if "goal" in system_prompt:
                return {"goal": "demo", "constraints": []}
            if "role and team_size" in system_prompt:
                if "Lead" in (user_prompt or ""):
                    return {"role": "lead", "team_size": None}
                if "5" in (user_prompt or ""):
                    return {"role": None, "team_size": "5"}
            if "architecture" in system_prompt:
                if "svc" in (user_prompt or ""):
                    return {"architecture": "svc", "key_technologies": [], "followup_hooks": []}
                return {"architecture": None, "key_technologies": ["python"], "followup_hooks": ["redis"]}
            if "constraints" in system_prompt and "list" in system_prompt:
                return {"constraints": ["latency"]}
            if "hardest_challenge" in system_prompt or "challenge" in system_prompt:
                return {"hardest_challenge": "scaling"}
            if "outcomes" in system_prompt or "metrics" in system_prompt:
                return {"outcomes": "100rps", "evaluation_metrics": {"throughput": "100rps"}}
            if "lessons" in system_prompt or "reflection" in system_prompt:
                return {"lessons": "tests"}
            return {"goal": "demo"}
        if task_name == "stage_2_parse":
            return {
                "skill_hooks": ["python"],
                "notes": ["api work"],
                "evaluation_metrics": {"latency": "100ms"},
                "followup_hooks": ["redis"],
            }
        if task_name == "question_generation":
            return {"question_text": "components?"}
        if task_name == "stage_3_question":
            return {"question_text": "What is Python?"}
        if task_name == "stage_3_eval":
            return {"result": "pass", "rationale": "ok"}
        if task_name == "stage_4_summary":
            return {"strengths": ["reasoning"], "risks": [], "follow_ups": []}
        return {}

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

    q4 = await orch.loop(state, "Lead")
    assert q4["question_type"] == "warmup_team_size"

    q5 = await orch.loop(state, "Team of 5")
    assert q5["question_type"] == "warmup_architecture"

    q6 = await orch.loop(state, "svc architecture")
    assert q6["question_type"] == "warmup_tech_stack"

    q7 = await orch.loop(state, "python and redis")
    assert q7["question_type"] == "warmup_constraints"

    q8 = await orch.loop(state, "latency under 100ms")
    assert q8["question_type"] == "warmup_challenge"

    q9 = await orch.loop(state, "scaling issues")
    assert q9["question_type"] == "warmup_resolution"

    q10 = await orch.loop(state, "used caching")
    assert q10["question_type"] == "warmup_outcome"

    q11 = await orch.loop(state, "100rps")
    assert q11["question_type"] == "warmup_reflection"

    q12 = await orch.loop(state, "better tests")
    assert q12["question_type"] == "evidence_components_list"

    q13 = await orch.loop(state, "listed components")
    assert q13["question_type"] == "evidence_component_details"

    q14 = await orch.loop(state, "component details")
    assert q14["question_type"] == "evidence_choice_space"

    q15 = await orch.loop(state, "considered options")
    assert q15["question_type"] == "evidence_decision_rationale"

    q16 = await orch.loop(state, "selected because")
    assert q16["question_type"] == "evidence_outcome_validation"

    q17 = await orch.loop(state, "it worked")
    assert q17["question_type"] == "evidence_tradeoff_exploration"

    q18 = await orch.loop(state, "tradeoffs considered")
    assert q18["question_type"] == "evidence_tradeoff_reasoning"

    q19 = await orch.loop(state, "why chosen")
    assert q19["question_type"] == "theory_primary"

    q20 = await orch.loop(state, "A language")
    assert q20["question_type"] == "theory_followup"

    q21 = await orch.loop(state, "deeper answer")
    assert q21["question_type"] == "wrapup_feedback"

    q22 = await orch.loop(state, "All good")
    assert q22["question_type"] == "wrapup_closing"

    q23 = await orch.loop(state)
    assert q23 is None
    assert state.packet.time_remaining_min == 0


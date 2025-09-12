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
            if "team_size" in system_prompt:
                return {"role": "lead", "team_size": "5"}
            if "architecture" in system_prompt:
                return {"architecture": "svc", "key_technologies": ["python"]}
            if "constraints" in system_prompt and "list" in system_prompt:
                return {"constraints": ["latency"]}
            if "hardest_challenge" in system_prompt or "challenge" in system_prompt:
                return {"hardest_challenge": "scaling"}
            if "outcomes" in system_prompt or "metrics" in system_prompt:
                return {"outcomes": "100rps"}
            if "lessons" in system_prompt or "reflection" in system_prompt:
                return {"lessons": "tests"}
            return {"goal": "demo"}
        if task_name == "stage_2_parse":
            return {
                "skill_hooks": ["python"],
                "notes": ["api work"],
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
    assert q2["question_type"] == "warmup_role"

    q3 = await orch.loop(state, "Lead of team 5")
    assert q3["question_type"] == "warmup_architecture"

    q4 = await orch.loop(state, "svc using python")
    assert q4["question_type"] == "warmup_constraints"

    q5 = await orch.loop(state, "latency under 100ms")
    assert q5["question_type"] == "warmup_challenge"

    q6 = await orch.loop(state, "scaling issues")
    assert q6["question_type"] == "warmup_outcome"

    q7 = await orch.loop(state, "100rps")
    assert q7["question_type"] == "warmup_reflection"

    q8 = await orch.loop(state, "better tests")
    assert q8["question_type"] == "evidence_components"

    q9 = await orch.loop(state, "component details")
    assert q9["question_type"] == "evidence_choice_space"

    q10 = await orch.loop(state, "considered options")
    assert q10["question_type"] == "evidence_decision_rationale"

    q11 = await orch.loop(state, "selected because")
    assert q11["question_type"] == "evidence_outcome_validation"

    q12 = await orch.loop(state, "it worked")
    assert q12["question_type"] == "evidence_tradeoff_reflection"

    q13 = await orch.loop(state, "tradeoffs considered")
    assert q13["question_type"] == "theory_primary"

    q14 = await orch.loop(state, "A language")
    assert q14["question_type"] == "theory_follow_up"

    q15 = await orch.loop(state, "deeper answer")
    assert q15["question_type"] == "wrapup_candidate_questions"

    q16 = await orch.loop(state, "No questions")
    assert q16["question_type"] == "wrapup_feedback"

    q17 = await orch.loop(state, "All good")
    assert q17 is None
    assert state.packet.time_remaining_min == 0


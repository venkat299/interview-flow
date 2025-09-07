import sys
from pathlib import Path
import types

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest

from orchestrator_service import Orchestrator
import orchestrator_service.orchestrator as orchestrator_module
from question_service import question_bank
from interviewer_service import LLMInterviewer
from monitor_service import LLMMonitor
from scoring_service import ScoringEngine
from adaptivity_service import AbilityModel
from sandbox_service.code_runner import run_code
from sandbox_service.sql_runner import run_query
from evidence_service import resume_parser, artifact_ingest
from guardrails_service import filters
from analytics_service import item_metrics
from verification_service import prober
from storage_service import storage
from orchestrator_service import llm_api as ai


@pytest.mark.asyncio
async def test_end_to_end_flow(monkeypatch):
    """Exercise the full interview flow across all services."""
    async def fake_intro():
        return "Welcome! Please introduce yourself."

    async def fake_soft(resume: str):
        return "Describe a challenge you overcame."

    monkeypatch.setattr(orchestrator_module, "generate_introductory_question", fake_intro)
    monkeypatch.setattr(orchestrator_module, "generate_soft_skill_question", fake_soft)

    orchestrator = Orchestrator()
    ability = AbilityModel()
    interviewer = LLMInterviewer()
    monitor = LLMMonitor()
    scoring = ScoringEngine()

    resume = "Worked with Python and SQL"
    claims_graph = resume_parser.parse_resume(resume)
    repo_meta = artifact_ingest.ingest_repo("https://github.com/example/repo")

    state = types.SimpleNamespace(
        current_phase="introduction",
        difficulty="beginner",
        resume_claims=[{"tech": "Python"}],
        current_topic=None,
    )
    context = {"job_description": "Backend role", "candidate_resume": resume}
    history: list[dict] = []

    intro = await orchestrator.decide_next_action(
        state, context, history, persona="friendly", question_func=lambda req: ""
    )
    assert "introduce" in intro.lower()

    state.current_phase = "soft_skills"
    soft = await orchestrator.decide_next_action(
        state, context, history, persona="friendly", question_func=lambda req: ""
    )
    assert "describe" in soft.lower()

    state.current_phase = None
    state.current_topic = {"name": "algorithms"}
    state.difficulty = "intermediate"

    async def question_func(req):
        item = question_bank.pick_item({"items": question_bank.load_items()}, {})
        return item["stem"]

    question = await orchestrator.decide_next_action(
        state, context, history, persona="friendly", question_func=question_func
    )
    assert await filters.check_question(question)
    assert await filters.anonymize_logs({"q": question}) == {"q": question}

    hook_payload = await ai.on_question_selected(question, {})
    paraphrased = hook_payload["question_text"]

    answer = "A hash table stores key value pairs using a hash function"
    code_result = run_code("python", "print('hi')", [])
    sql_result = run_query({}, [], "SELECT 1")
    assert code_result["passed"] and sql_result == []

    scored = await ai.on_answer_scored(paraphrased, answer, {})
    ability.update("algorithms", {"score": scored["score"]["correctness"]}, 0.1)
    assert ability.recommend_next()["skill"] == "algorithms"

    await item_metrics.update_stats("q1", 1.0, 1.0)
    await item_metrics.record_feedback("q1", 0.5)

    claim = await prober.select_claim({"resume_claims": state.resume_claims})
    probe = await prober.generate_probe(claim)
    assert "python" in probe.lower()

    storage.save_transcript("session", [{"question": paraphrased, "answer": answer}])
    storage.save_decision({"final": scored})

    assert "Python" in claims_graph["claims"]
    assert repo_meta["status"] == "ingested"

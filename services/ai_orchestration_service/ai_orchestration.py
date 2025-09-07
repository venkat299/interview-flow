"""Compatibility shim for legacy imports.

Proxies AI orchestration functions to the current implementation in
`services/orchestrator_service/llm_api.py` so existing imports like
`from ai_orchestration_service import ai_orchestration as ai` continue to work.
"""

from orchestrator_service.llm_api import (
    generate_introductory_question,
    generate_soft_skill_question,
    generate_next_question,
    create_interview_blueprint,
    evaluate_candidate_answer,
    on_question_selected,
    on_answer_scored,
    generate_final_summary,
)

__all__ = [
    "generate_introductory_question",
    "generate_soft_skill_question",
    "generate_next_question",
    "create_interview_blueprint",
    "evaluate_candidate_answer",
    "on_question_selected",
    "on_answer_scored",
    "generate_final_summary",
]


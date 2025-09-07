"""AI orchestration legacy namespace.

This package provides a shim to the current orchestrator implementation.
"""

from .ai_orchestration import (
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


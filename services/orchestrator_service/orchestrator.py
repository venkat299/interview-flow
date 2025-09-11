"""Stage-based orchestrator coordinating interview questions."""

from typing import Any, Optional

from .llm_api import (
    warmup_select_project,
    warmup_role_context,
    warmup_architecture,
    warmup_constraints,
    warmup_challenge,
    warmup_outcome,
    warmup_reflection,
    evidence_components,
    evidence_skill_task,
    theory_check_question,
    wrapup_closure,
)
from session_service.question_log_db import log_question_response


class Orchestrator:
    """Dispatches to stage-specific LLM helpers based on interview state."""

    async def decide_next_action(
        self, state: Any, answer: Optional[str] = None
    ) -> Optional[dict]:
        packet = state.packet
        phase = state.current_phase

        if phase == "warm_up":
            if answer is not None and getattr(state, "last_question_text", None):
                log_question_response(
                    stage=phase,
                    question_type=getattr(state, "last_question_type", ""),
                    question_text=getattr(state, "last_question_text", ""),
                    answer_text=answer,
                    session_id=getattr(state, "session_id", None),
                    candidate_id=getattr(state, "candidate_id", None),
                )
            step = state.current_warmup_step
            func_map = {
                "select_project": warmup_select_project,
                "role_context": warmup_role_context,
                "architecture": warmup_architecture,
                "constraints": warmup_constraints,
                "challenge": warmup_challenge,
                "outcome": warmup_outcome,
                "reflection": warmup_reflection,
            }
            q = await func_map[step](packet, answer)
            if q is None:
                state.advance_warmup_step()
                return await self.decide_next_action(state, None)
            state.last_question_text = q.get("question_text")
            state.last_question_type = q.get("question_type")
            return q

        if phase == "evidence":

            if answer is not None and getattr(state, "last_question_text", None):
                log_question_response(
                    stage=phase,
                    question_type=getattr(state, "last_question_type", ""),
                    question_text=getattr(state, "last_question_text", ""),
                    answer_text=answer,
                    session_id=getattr(state, "session_id", None),
                    candidate_id=getattr(state, "candidate_id", None),
                )
            q = await evidence_skill_question(packet, answer)

            if q is None:
                state.advance_evidence_step()
                return await self.decide_next_action(state, None)
            state.last_question_text = q
            state.last_question_type = "evidence_skill"
            return {"question_text": q, "question_type": "evidence_skill"}


        if phase == "theory":
            if answer is not None and getattr(state, "last_question_text", None):
                log_question_response(
                    stage=phase,
                    question_type=getattr(state, "last_question_type", ""),
                    question_text=getattr(state, "last_question_text", ""),
                    answer_text=answer,
                    session_id=getattr(state, "session_id", None),
                    candidate_id=getattr(state, "candidate_id", None),
                )
            q = await theory_check_question(packet, answer)
            if q is None:
                state.advance_phase()
                return await self.decide_next_action(state, None)
            state.last_question_text = q
            state.last_question_type = "theory_check"
            return {"question_text": q, "question_type": "theory_check"}

        if phase == "wrap_up":
            if answer is not None and getattr(state, "last_question_text", None):
                log_question_response(
                    stage=phase,
                    question_type=getattr(state, "last_question_type", ""),
                    question_text=getattr(state, "last_question_text", ""),
                    answer_text=answer,
                    session_id=getattr(state, "session_id", None),
                    candidate_id=getattr(state, "candidate_id", None),
                )
            q = await wrap_up(packet, answer)
            if q is None:
                state.advance_phase()
                return None
            state.last_question_text = q
            state.last_question_type = "wrap_up"
            return {"question_text": q, "question_type": "wrap_up"}


        return None

    async def loop(self, state: Any, answer: Optional[str] = None) -> Optional[dict]:
        """Return the next question payload or None if the interview has ended."""
        return await self.decide_next_action(state, answer)

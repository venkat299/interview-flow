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


class Orchestrator:
    """Dispatches to stage-specific LLM helpers based on interview state."""

    async def decide_next_action(
        self, state: Any, answer: Optional[str] = None
    ) -> Optional[dict]:
        packet = state.packet
        phase = state.current_phase

        if phase == "warm_up":
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
            return q

        if phase == "evidence":
            step = state.current_evidence_step
            func_map = {
                "components": evidence_components,
                "skill_task": evidence_skill_task,
            }
            q = await func_map[step](packet, answer)
            if q is None:
                state.advance_evidence_step()
                return await self.decide_next_action(state, None)
            return q

        if phase == "theory":
            q = await theory_check_question(packet, answer)
            if q is None:
                state.advance_phase()
                return await self.decide_next_action(state, None)
            return {"question_text": q, "question_type": "theory_check"}

        if phase == "wrap_up":
            if state.wrapup_index >= len(state.wrapup_steps):
                return None
            step = state.current_wrapup_step
            func_map = {"closure": wrapup_closure}
            q = await func_map[step](packet, answer)
            if q is None:
                state.advance_wrapup_step()
                return await self.decide_next_action(state, None)
            return q

        return None

    async def loop(self, state: Any, answer: Optional[str] = None) -> Optional[dict]:
        """Return the next question payload or None if the interview has ended."""
        return await self.decide_next_action(state, answer)

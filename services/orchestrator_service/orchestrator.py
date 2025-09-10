"""Stage-based orchestrator coordinating interview questions."""

from typing import Any, Optional

from .llm_api import (
    warmup_overview,
    warmup_constraint,
    evidence_skill_question,
    theory_check_question,
    wrap_up,
)


class Orchestrator:
    """Dispatches to stage-specific LLM helpers based on interview state."""

    async def decide_next_action(
        self, state: Any, answer: Optional[str] = None
    ) -> Optional[str]:
        packet = state.packet
        phase = state.current_phase

        if phase == "warm_up":
            if state.warmup_step == 0:
                q = await warmup_overview(packet, answer)
                if q is None:
                    state.warmup_step = 1
                    return await self.decide_next_action(state, None)
                return q
            q = await warmup_constraint(packet, answer)
            if q is None:
                state.advance_phase()
                return await self.decide_next_action(state, None)
            return q

        if phase == "evidence":
            q = await evidence_skill_question(packet, answer)
            if q is None:
                state.advance_phase()
                return await self.decide_next_action(state, None)
            return q

        if phase == "theory":
            q = await theory_check_question(packet, answer)
            if q is None:
                state.advance_phase()
                return await self.decide_next_action(state, None)
            return q

        if phase == "wrap_up":
            q = await wrap_up(packet, answer)
            if q is None:
                state.advance_phase()
            return q

        return None

    async def loop(self, state: Any, answer: Optional[str] = None) -> Optional[str]:
        """Return the next question string or None if the interview has ended."""
        return await self.decide_next_action(state, answer)

    async def record_turn(self, turn: dict) -> None:  # pragma: no cover - placeholder
        return None


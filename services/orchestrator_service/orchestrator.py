"""Stage-based orchestrator coordinating interview questions."""

from typing import Any, Optional

from .llm_api import (
    theory_primary_question,
    theory_followup_question,
    wrapup_feedback,
    wrapup_closing,
)
from .followups import build_followup_question, update_followup_hooks
from session_service.question_log_db import log_question_response


class Orchestrator:
    """Dispatches to stage-specific LLM helpers based on interview state."""

    async def decide_next_action(
        self, state: Any, answer: Optional[str] = None
    ) -> Optional[dict]:
        packet = state.packet
        phase = state.current_phase

        # Handle answer to a targeted follow-up probe
        if answer is not None and getattr(state, "last_question_type", None) == "targeted_followup":
            log_question_response(
                stage=phase,
                question_type="targeted_followup",
                question_text=getattr(state, "last_question_text", ""),
                answer_text=answer,
                session_id=getattr(state, "session_id", None),
                candidate_id=getattr(state, "candidate_id", None),
            )

            update_followup_hooks(packet, answer, addressed_hook=state.last_followup_hook)
            state.last_followup_hook = None

            return await self.decide_next_action(state, None)

        # Insert targeted follow-up questions when hooks are present
        if answer is None:
            pending = [
                h
                for h in packet.followup_hooks
                if h not in state.probed_followup_hooks
                and h not in packet.resolved_followup_hooks
            ]
            for hook in pending:
                q_text = build_followup_question(hook)
                state.probed_followup_hooks.add(hook)
                if q_text:
                    state.last_question_text = q_text
                    state.last_question_type = "targeted_followup"
                    state.last_followup_hook = hook
                    return {"question_text": q_text, "question_type": "targeted_followup"}

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
            skills = packet.followup_hooks or packet.skill_hooks or packet.jd_core_skills
            if state.theory_skill_index >= len(skills):
                state.advance_phase()
                return await self.decide_next_action(state, None)
            step = state.current_theory_step
            skill = skills[state.theory_skill_index]
            func_map = {
                "primary": theory_primary_question,
                "followup": theory_followup_question,
            }
            q = await func_map[step](packet, skill, answer)
            if q is None:
                state.advance_theory_step()
                return await self.decide_next_action(state, None)
            state.last_question_text = q.get("question_text")
            state.last_question_type = q.get("question_type")
            return q

        if phase == "wrap_up":
            if state.wrapup_index >= len(state.wrapup_steps):
                state.advance_phase()
                return None
            step = state.current_wrapup_step
            func_map = {
                "feedback": wrapup_feedback,
                "closing": wrapup_closing,
            }
            if step == "closing":
                q = await func_map[step](packet)
                # Log the final closing prompt even though no answer is expected
                log_question_response(
                    stage=phase,
                    question_type=step,
                    question_text=q.get("question_text", ""),
                    answer_text="",
                    session_id=getattr(state, "session_id", None),
                    candidate_id=getattr(state, "candidate_id", None),
                )
                state.advance_wrapup_step()
                return q
            q = await func_map[step](packet, answer)
            if answer is not None and getattr(state, "last_question_text", None):
                log_question_response(
                    stage=phase,
                    question_type=step,
                    question_text=getattr(state, "last_question_text", ""),
                    answer_text=answer,
                    session_id=getattr(state, "session_id", None),
                    candidate_id=getattr(state, "candidate_id", None),
                )
            if q is None:
                state.advance_wrapup_step()
                return await self.decide_next_action(state, None)
            state.last_question_text = q.get("question_text")
            state.last_question_type = q.get("question_type")
            return q


        return None

    async def loop(self, state: Any, answer: Optional[str] = None) -> Optional[dict]:
        """Return the next question payload or None if the interview has ended."""
        return await self.decide_next_action(state, answer)

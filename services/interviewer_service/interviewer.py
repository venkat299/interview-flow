"""LLM Interviewer module for generating conversational prompts."""
from typing import Dict, List
import logging

from gateway_service import gateway
from .personas import PERSONA_PROMPTS


logger = logging.getLogger(__name__)


class LLMInterviewer:
    """Handles phrasing and flow of questions to the candidate."""

    async def next_question(self, context: Dict, item: Dict) -> str:
        """Paraphrase a bank item into a friendly question."""
        stem = item.get("stem", "")

        persona_key = context.get("persona", "friendly_mentor")
        persona_prompt = PERSONA_PROMPTS.get(persona_key, "")

        history: List[Dict] = context.get("history") or []
        recent = "\n".join(
            f"{turn.get('role')}: {turn.get('message')}" for turn in history[-4:]
        )

        role_skill_tags: List[str] = context.get("role_skill_tags") or []
        skill_hooks: List[str] = context.get("skill_hooks") or []
        recent_hooks = ", ".join(skill_hooks[-3:])

        system_prompt = (
            f"{persona_prompt}\n"
            "Rephrase the interview question with a natural, conversational tone."
        )

        prompt_lines = [
            f"Original question: {stem}",
            f"Conversation so far:\n{recent}",
        ]
        if role_skill_tags:
            prompt_lines.append(
                "Role skill tags: " + ", ".join(role_skill_tags)
            )
        if recent_hooks:
            prompt_lines.append(
                "Recent skill hooks: " + recent_hooks
            )
        prompt_lines.append("Return only the rephrased question.")
        user_prompt = "\n".join(prompt_lines)

        try:
            data = await gateway.execute_task(
                task_name="question_generation",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            return data.get("question_text", stem)
        except Exception:
            logger.exception("Gateway question generation failed; using original stem")
            return stem

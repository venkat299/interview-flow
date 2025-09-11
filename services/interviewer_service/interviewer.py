"""LLM Interviewer module for generating conversational prompts."""
from typing import Dict, List

from gateway_service import gateway
from .personas import PERSONA_PROMPTS


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

        system_prompt = (
            f"{persona_prompt}\n"
            "Rephrase the interview question with a natural, conversational tone."
        )
        user_prompt = (
            f"Original question: {stem}\n"
            f"Conversation so far:\n{recent}\n"
            "Return only the rephrased question."
        )

        try:
            data = await gateway.execute_task(
                task_name="question_generation",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            return data.get("question_text", stem)
        except Exception:
            return stem

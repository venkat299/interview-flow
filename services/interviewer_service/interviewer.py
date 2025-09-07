"""LLM Interviewer module for generating conversational prompts."""
from typing import Dict


class LLMInterviewer:
    """Handles phrasing and flow of questions to the candidate."""

    async def next_question(self, context: Dict, item: Dict) -> str:
        """Paraphrase a bank item into a friendly question."""
        stem = item.get("stem", "")
        return f"{stem}"  # Placeholder paraphrasing logic

    async def warm_start(self, resume: str) -> str:
        """Generate rapport-building intro and diagnostic."""
        return "Let's get started. Could you briefly walk me through your experience?"

    async def wrap_up(self, state: Dict) -> str:
        """Produce a final summary question."""
        return "Thanks for your time today. Any reflections before we conclude?"

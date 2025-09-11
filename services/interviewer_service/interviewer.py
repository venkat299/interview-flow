"""LLM Interviewer module for generating conversational prompts."""
from typing import Dict


class LLMInterviewer:
    """Handles phrasing and flow of questions to the candidate."""

    async def next_question(self, context: Dict, item: Dict) -> str:
        """Paraphrase a bank item into a friendly question."""
        stem = item.get("stem", "")
        return f"{stem}"  # Placeholder paraphrasing logic

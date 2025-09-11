"""LLM Monitor module for shadow evaluation of interview turns."""
from typing import Dict


class LLMMonitor:
    """Evaluates clarity, relevance, and pacing of each turn."""

    async def assess_turn(self, state: Dict, question: str, answer: str) -> Dict:
        """Return metrics about the candidate's response."""
        return {"clarity": 1.0, "relevance": 1.0, "est_difficulty": 3}

"""Question generator for natural paraphrasing."""
from typing import Dict


def paraphrase(item: Dict, style: str = "neutral") -> str:
    """Return a natural language version of a question stem."""
    return item.get("stem", "")

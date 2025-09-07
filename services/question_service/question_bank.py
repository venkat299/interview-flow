"""Utilities for loading and selecting interview questions."""
from typing import Dict, List


def load_items() -> List[Dict]:
    """Load a seed bank of questions with tags and tests."""
    # Placeholder question bank with minimal metadata
    return [
        {
            "id": "q1",
            "stem": "What is a hash table?",
            "skill_tags": ["algorithms"],
            "tests": []
        }
    ]


def pick_item(state: Dict, monitor_diag: Dict) -> Dict:
    """Select the next question based on state and monitor diagnostics."""
    items = state.get("items") or load_items()
    return items[0]

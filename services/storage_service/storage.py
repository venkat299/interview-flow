"""Storage utilities for transcripts and audit data."""
from typing import Any, Dict, List


def save_transcript(session_id: str, turns: List[Dict[str, Any]]) -> None:
    """Persist the full transcript for a session."""
    # Stub: in-memory or file-based storage could be used here
    return None


def save_decision(state: Dict[str, Any]) -> None:
    """Store model prompts, IDs, and scoring decisions."""
    return None

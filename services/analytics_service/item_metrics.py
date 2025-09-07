"""Question quality analytics utilities."""
"""Question quality analytics utilities."""


async def update_stats(item_id: str, score: float, time: float) -> None:
    """Update difficulty and discrimination metrics for an item."""
    _ = (item_id, score, time)
    return None


async def record_feedback(item_id: str, clarity_rating: float, note: str | None = None) -> None:
    """Capture candidate clarity feedback for an item."""
    _ = (item_id, clarity_rating, note)
    return None

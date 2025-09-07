"""Resume parsing utilities for building a claims graph."""
from typing import Dict, List


def parse_resume(text: str) -> Dict[str, List[str]]:
    """Parse resume text into a simple claims structure."""
    # Stub parser: split into words and treat unique terms as claims
    words = set(text.split())
    return {"claims": list(words)}

"""SQL sandbox for running queries against isolated data."""
from typing import Any, Dict, List


def run_query(schema: Dict[str, str], data: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    """Execute a SQL query and return results."""
    # Stub implementation; in reality would use an embedded database
    return []

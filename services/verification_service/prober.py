"""Resume claim verification helpers."""
from typing import Dict, Optional


async def select_claim(state: Dict) -> Optional[Dict]:
    """Pick a resume claim to probe based on interview state.

    Parameters
    ----------
    state: Dict
        Current interview state containing resume claims.
    Returns
    -------
    Optional[Dict]
        Claim object to probe, if any.
    """
    claims = (state or {}).get("resume_claims", [])
    return claims[0] if claims else None


async def generate_probe(claim: Dict) -> str:
    """Generate a probing question for the given claim.

    Parameters
    ----------
    claim: Dict
        Claim metadata describing the resume statement.
    Returns
    -------
    str
        A natural language probe to verify the claim.
    """
    if not claim:
        return "Could you elaborate on your experience?"
    tech = claim.get("tech") or claim.get("project") or "this"
    return f"In your resume you mentioned work with {tech}. Can you share more details?"

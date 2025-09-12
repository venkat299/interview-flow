"""Canonical skill tags keyed by role.

These curated tags act as a bootstrap during Stage 0 of the interview flow.
They provide a starting point for the LLM to reason about relevant topics even
before analyzing the job description or resume. The tags are intentionally
high level and non-exhaustive; additional tags will be discovered at runtime
and merged with these canonical ones.
"""

SKILL_INVENTORY = {
    # Backend engineers often need to reason about systems level concerns.
    "backend": [
        "scaling",
        "caching",
    ],
    # Frontend work emphasises user interfaces and state handling.
    "frontend": [
        "state management",
        "responsive design",
        "component architecture",
    ],
    # Operational roles focus on deploying and maintaining services.
    "devops": [
        "ci/cd",
        "containerization",
        "monitoring",
    ],
    # Data science and ML oriented roles.
    "data_science": [
        "model training",
        "feature engineering",
        "data visualization",
    ],
}


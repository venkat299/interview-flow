"""Topic inference service for interview preparation."""
from typing import List

from schemas.interview import InterviewContext


async def determine_topics(context: InterviewContext) -> List[str]:
    """Infer interview topics from job description and resume.

    This is a placeholder implementation that extracts simple keyword-based
    topics. A real implementation would call an LLM to perform deeper
    analysis.
    """

    text = f"{context.job_description} {context.candidate_resume or ''}".lower()
    keywords = ["python", "javascript", "java", "frontend", "backend", "database"]
    topics = [word for word in keywords if word in text]
    return topics or ["general"]

"""DSPy program for Stage-0 analysis of job description and resume."""
from __future__ import annotations

from typing import List, Optional

import dspy
from pydantic import BaseModel, Field

from gateway_service import gateway


class JDResumeAnalysisInput(BaseModel):
    """Input payload for analyzing a JD and resume."""

    jd_text: str = Field(..., description="Raw job description text")
    resume_text: str = Field(..., description="Candidate resume text")


class JDResumeAnalysisOutput(BaseModel):
    """Normalized analysis extracted from the LLM."""

    role_from_jd: Optional[str] = None
    jd_core_skills: List[str] = Field(default_factory=list)
    resume_claims: List[str] = Field(default_factory=list)
    overlap_skills: List[str] = Field(default_factory=list)
    primary_overlap_focus: Optional[str] = None
    selected_project: Optional[str] = None
    experience_plan: List[str] = Field(default_factory=list)


class Stage0AnalysisProgram(dspy.Module):
    """Thin DSPy wrapper that delegates to the gateway service."""

    system_prompt: str = (
        "Read the job description and resume. Return JSON with the following keys: "
        "role_from_jd, jd_core_skills (list), resume_claims (list), "
        "overlap_skills (list), primary_overlap_focus, selected_project (string), "
        "experience_plan (ordered list of warm-up/evidence slot identifiers)."
    )

    async def __call__(self, inp: JDResumeAnalysisInput) -> JDResumeAnalysisOutput:
        data = await gateway.execute_task(
            task_name="stage_0_analysis",
            system_prompt=self.system_prompt,
            user_prompt=f"Job description:\n{inp.jd_text}\n\nResume:\n{inp.resume_text}",
        )
        return JDResumeAnalysisOutput.model_validate(data)

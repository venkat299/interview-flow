"""DSPy program for Stage-2 focus area interview planning."""
from __future__ import annotations

from typing import List

import dspy
from pydantic import BaseModel, Field

from gateway_service import gateway
from ..schemas import FocusAreaQuestions


PROMPT_PREAMBLE = """You are an expert AI technical recruiter. Your task is to analyze the provided Job Description (JD) and Resume to create a structured interview question guide.

Follow these instructions precisely:

    Analyze and Synthesize: First, identify the key intersections between the JD's requirements (e.g., skills, responsibilities) and the candidate's experience (e.g., projects, roles).

    Define Focus Areas: Based on your analysis, define 5 distinct and logical Focus Areas for a technical interview. Each Focus Area's name should be clear and concise (e.g., \"Productionization & MLOps,\" \"Modeling & Algorithms\").

    Generate Questions: For each of the 5 Focus Areas, you must generate exactly 4 questions that are directly relevant to the JD and resume.

    Adhere to Question Constraints:

        Question Types: The 4 questions for each area must be categorized as:

            2 reasoning questions: These should probe the \"why\" and \"how\" behind the candidate's decisions and experiences.

            2 conceptual questions: These should test factual or definitional knowledge of tools and concepts mentioned.

        Simplicity: All questions must be non-compound. Do not ask two things in one question.

        Brevity: Each question must be concise, limited to a maximum of one or two lines.

    Format Output as JSON: The final output must be a single, well-formed JSON object. Use the following structure:

{
  \"interview_focus_areas\": [
    {
      \"area_name\": \"Example: Project & Problem Formulation\",
      \"reasoning_questions\": [
        \"Question 1...\",
        \"Question 2...\"
      ],
      \"conceptual_questions\": [
        \"Question 1...\",
        \"Question 2...\"
      ]
    },
    {
      \"area_name\": \"Focus Area 2 Name...\",
      \"reasoning_questions\": [
        \"...\",
        \"...\"
      ],
      \"conceptual_questions\": [
        \"...\",
        \"...\"
      ]
    }
  ]
}

[INSERT JOB DESCRIPTION HERE]
"""

PROMPT_RESUME_HEADER = "[INSERT RESUME HERE]"


class Stage2QAInput(BaseModel):
    """Inputs for generating focus areas and questions."""

    jd_text: str = Field(default="", description="Raw job description text")
    resume_text: str = Field(default="", description="Candidate resume text")


class Stage2QAOutput(BaseModel):
    """Structured focus areas returned by the LLM."""

    interview_focus_areas: List[FocusAreaQuestions] = Field(default_factory=list)


class Stage2QAProgram(dspy.Module):
    """Request a focus-area driven interview plan from a dedicated LLM."""

    async def __call__(self, inp: Stage2QAInput) -> Stage2QAOutput:
        prompt = (
            f"{PROMPT_PREAMBLE}\n\n{inp.jd_text or 'Not provided'}"
            f"\n\n{PROMPT_RESUME_HEADER}\n\n{inp.resume_text or 'Not provided'}"
        )
        data = await gateway.execute_task(
            task_name="stage_2_focus_plan",
            system_prompt=prompt,
        )
        return Stage2QAOutput.model_validate(data)

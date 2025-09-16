from orchestrator_service.programs.stage0_analysis import JDResumeAnalysisOutput


def test_primary_overlap_focus_accepts_list():
    raw_output = {
        "role_from_jd": "backend",
        "jd_core_skills": ["python"],
        "resume_claims": ["python"],
        "overlap_skills": ["python"],
        "primary_overlap_focus": [
            "Python + SQL driven data pipelines",
            "Time-series modeling",
        ],
    }

    parsed = JDResumeAnalysisOutput.model_validate(raw_output)

    assert (
        parsed.primary_overlap_focus
        == "Python + SQL driven data pipelines, Time-series modeling"
    )


def test_primary_overlap_focus_handles_empty_list():
    raw_output = {
        "role_from_jd": "backend",
        "jd_core_skills": ["python"],
        "resume_claims": ["python"],
        "overlap_skills": ["python"],
        "primary_overlap_focus": [],
    }

    parsed = JDResumeAnalysisOutput.model_validate(raw_output)

    assert parsed.primary_overlap_focus is None

import json
import sqlite3

import pytest

from session_service.question_log_db import (
    init_db,
    log_question_response,
    log_focus_area_response,
)


def test_log_question_response_captures_question_and_answer(tmp_path):
    db_path = tmp_path / "question_logs.db"
    init_db(db_path)
    evaluation_payload = {
        "evaluation_type": "Reasoning",
        "overall_score": 4.25,
        "dimensional_scores": {
            "problem_comprehension": {"score": 4, "justification": "Understood"}
        },
    }
    log_question_response(
        stage="theory",
        question_type="primary",
        question_text="What is Python?",
        answer_text="A language",
        session_id="s1",
        job_id="job-42",
        resume_id="resume-99",
        candidate_id="c1",
        evaluation=evaluation_payload,
        db_path=db_path,
    )
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            stage,
            question_type,
            question_text,
            answer_text,
            job_id,
            resume_id,
            evaluation_type,
            evaluation_detail,
            evaluation_score
        FROM question_logs
        """
    )
    row = cur.fetchone()
    conn.close()
    assert row[:6] == (
        "theory",
        "primary",
        "What is Python?",
        "A language",
        "job-42",
        "resume-99",
    )
    assert row[6] == "Reasoning"
    stored_detail = json.loads(row[7])
    assert pytest.approx(stored_detail["overall_score"], rel=1e-6) == 4.25
    assert pytest.approx(row[8], rel=1e-6) == 4.25


def test_focus_area_logs_store_evaluations_and_averages(tmp_path):
    db_path = tmp_path / "question_logs.db"
    init_db(db_path)
    reasoning_eval = {
        "evaluation_type": "Reasoning",
        "overall_score": 4.0,
        "dimensional_scores": {
            "problem_comprehension": {"score": 5, "justification": "Great"},
            "analysis_of_trade_offs": {"score": 3, "justification": "Average"},
        },
    }
    conceptual_eval = {
        "evaluation_type": "Conceptual",
        "overall_score": 3.0,
        "dimensional_scores": {
            "factual_accuracy": {"score": 2, "justification": "Partial"},
            "clarity_of_explanation": {"score": 4, "justification": "Clear"},
        },
    }
    log_focus_area_response(
        focus_area="Python Mastery",
        question_type="qa_reasoning",
        question_text="Why did you choose Python?",
        answer_text="Because of the ecosystem",
        session_id="s1",
        job_id="job-42",
        resume_id="resume-99",
        candidate_id="c1",
        evaluation=reasoning_eval,
        db_path=db_path,
    )
    log_focus_area_response(
        focus_area="Python Mastery",
        question_type="qa_conceptual",
        question_text="What is a Python decorator?",
        answer_text="It wraps a function",
        session_id="s1",
        job_id="job-42",
        resume_id="resume-99",
        candidate_id="c1",
        evaluation=conceptual_eval,
        db_path=db_path,
    )

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT focus_area, question_type, evaluation_type, evaluation_score
        FROM focus_area_logs
        ORDER BY id
        """
    )
    rows = cur.fetchall()
    assert rows[0] == ("Python Mastery", "qa_reasoning", "Reasoning", pytest.approx(4.0))
    assert rows[1] == ("Python Mastery", "qa_conceptual", "Conceptual", pytest.approx(3.0))

    cur.execute(
        """
        SELECT total_score, sample_size, average_score
        FROM focus_area_averages
        WHERE session_id = ? AND focus_area = ?
        """,
        ("s1", "Python Mastery"),
    )
    total_score, sample_size, average_score = cur.fetchone()
    assert pytest.approx(total_score, rel=1e-6) == 7.0
    assert sample_size == 2
    assert pytest.approx(average_score, rel=1e-6) == 3.5

    cur.execute(
        """
        SELECT evaluation_type, dimension_name, average_score, sample_size
        FROM dimension_averages
        WHERE session_id = ?
        ORDER BY evaluation_type, dimension_name
        """,
        ("s1",),
    )
    dim_rows = cur.fetchall()
    reasoning_dims = {
        (etype, name): (avg, count)
        for etype, name, avg, count in dim_rows
        if etype == "Reasoning"
    }
    conceptual_dims = {
        (etype, name): (avg, count)
        for etype, name, avg, count in dim_rows
        if etype == "Conceptual"
    }
    assert reasoning_dims[("Reasoning", "problem_comprehension")] == (
        pytest.approx(5.0),
        1,
    )
    assert conceptual_dims[("Conceptual", "factual_accuracy")] == (
        pytest.approx(2.0),
        1,
    )
    conn.close()

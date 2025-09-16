import sqlite3
from session_service.question_log_db import (
    init_db,
    log_question_response,
    log_focus_area_response,
)


def test_log_question_response_captures_question_and_answer(tmp_path):
    db_path = tmp_path / "question_logs.db"
    init_db(db_path)
    log_question_response(
        stage="theory",
        question_type="primary",
        question_text="What is Python?",
        answer_text="A language",
        session_id="s1",
        candidate_id="c1",
        db_path=db_path,
    )
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT stage, question_type, question_text, answer_text FROM question_logs"
    )
    row = cur.fetchone()
    conn.close()
    assert row == (
        "theory",
        "primary",
        "What is Python?",
        "A language",
    )


def test_log_focus_area_response_persists_focus_area(tmp_path):
    db_path = tmp_path / "question_logs.db"
    init_db(db_path)
    log_focus_area_response(
        focus_area="Python Mastery",
        question_type="qa_reasoning",
        question_text="Why did you choose Python?",
        answer_text="Because of the ecosystem",
        session_id="s1",
        candidate_id="c1",
        db_path=db_path,
    )
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT focus_area, question_type, question_text, answer_text FROM focus_area_logs"
    )
    row = cur.fetchone()
    conn.close()
    assert row == (
        "Python Mastery",
        "qa_reasoning",
        "Why did you choose Python?",
        "Because of the ecosystem",
    )

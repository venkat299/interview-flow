import sqlite3
from session_service.question_log_db import init_db, log_question_response


def test_log_question_response_captures_question_and_answer(tmp_path):
    db_path = tmp_path / "question_logs.db"
    init_db(db_path)
    log_question_response(
        stage="evidence",
        question_type="choice_space",
        question_text="What options did you consider?",
        answer_text="Option A and B",
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
        "evidence",
        "choice_space",
        "What options did you consider?",
        "Option A and B",
    )

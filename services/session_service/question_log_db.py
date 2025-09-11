import sqlite3
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).resolve().with_name("question_logs.db")


def init_db(db_path: Path = DB_PATH) -> None:
    """Initialize the SQLite database for question/answer logs."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS question_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            candidate_id TEXT,
            stage TEXT,
            question_type TEXT,
            question_text TEXT,
            answer_text TEXT,
            timestamp TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def log_question_response(
    stage: str,
    question_type: str,
    question_text: str,
    answer_text: str,
    session_id: Optional[str] = None,
    candidate_id: Optional[str] = None,
    db_path: Path = DB_PATH,
) -> None:
    """Persist a single question/answer pair to the log database."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO question_logs (session_id, candidate_id, stage, question_type, question_text, answer_text, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            session_id,
            candidate_id,
            stage,
            question_type,
            question_text,
            answer_text,
            datetime.now(UTC).isoformat(),
        ),
    )
    conn.commit()
    conn.close()


# Ensure the database exists on import
init_db()

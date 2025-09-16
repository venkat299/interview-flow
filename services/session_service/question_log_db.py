import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).resolve().with_name("question_logs.db")


def _ensure_columns(cur: sqlite3.Cursor, table: str, definitions: dict[str, str]) -> None:
    """Add any missing columns defined in ``definitions`` to ``table``."""

    cur.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cur.fetchall()}
    for column, ddl in definitions.items():
        if column not in existing:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def init_db(db_path: Path = DB_PATH) -> None:
    """Initialize the SQLite database for question/answer logs."""

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS question_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            job_id TEXT,
            resume_id TEXT,
            candidate_id TEXT,
            stage TEXT,
            question_type TEXT,
            question_text TEXT,
            answer_text TEXT,
            evaluation_detail TEXT,
            evaluation_score REAL,
            timestamp TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS focus_area_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            job_id TEXT,
            resume_id TEXT,
            candidate_id TEXT,
            focus_area TEXT,
            question_type TEXT,
            question_text TEXT,
            answer_text TEXT,
            evaluation_detail TEXT,
            evaluation_score REAL,
            timestamp TEXT
        )
        """
    )

    question_columns = {
        "session_id": "session_id TEXT",
        "job_id": "job_id TEXT",
        "resume_id": "resume_id TEXT",
        "candidate_id": "candidate_id TEXT",
        "stage": "stage TEXT",
        "question_type": "question_type TEXT",
        "question_text": "question_text TEXT",
        "answer_text": "answer_text TEXT",
        "evaluation_detail": "evaluation_detail TEXT",
        "evaluation_score": "evaluation_score REAL",
        "timestamp": "timestamp TEXT",
    }
    focus_area_columns = {
        "session_id": "session_id TEXT",
        "job_id": "job_id TEXT",
        "resume_id": "resume_id TEXT",
        "candidate_id": "candidate_id TEXT",
        "focus_area": "focus_area TEXT",
        "question_type": "question_type TEXT",
        "question_text": "question_text TEXT",
        "answer_text": "answer_text TEXT",
        "evaluation_detail": "evaluation_detail TEXT",
        "evaluation_score": "evaluation_score REAL",
        "timestamp": "timestamp TEXT",
    }

    _ensure_columns(cur, "question_logs", question_columns)
    _ensure_columns(cur, "focus_area_logs", focus_area_columns)

    conn.commit()
    conn.close()


def log_question_response(
    stage: str,
    question_type: str,
    question_text: str,
    answer_text: str,
    session_id: Optional[str] = None,
    job_id: Optional[str] = None,
    resume_id: Optional[str] = None,
    candidate_id: Optional[str] = None,
    evaluation_detail: Optional[str] = None,
    evaluation_score: Optional[float] = None,
    db_path: Path = DB_PATH,
) -> None:
    """Persist a single question/answer pair to the log database."""

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO question_logs (
            session_id,
            job_id,
            resume_id,
            candidate_id,
            stage,
            question_type,
            question_text,
            answer_text,
            evaluation_detail,
            evaluation_score,
            timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            job_id,
            resume_id,
            candidate_id,
            stage,
            question_type,
            question_text,
            answer_text,
            evaluation_detail,
            evaluation_score,
            datetime.now(UTC).isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def log_focus_area_response(
    focus_area: str,
    question_type: str,
    question_text: str,
    answer_text: str,
    session_id: Optional[str] = None,
    job_id: Optional[str] = None,
    resume_id: Optional[str] = None,
    candidate_id: Optional[str] = None,
    evaluation_detail: Optional[str] = None,
    evaluation_score: Optional[float] = None,
    db_path: Path = DB_PATH,
) -> None:
    """Persist focus area question/answer data for later evaluation."""

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO focus_area_logs (
            session_id,
            job_id,
            resume_id,
            candidate_id,
            focus_area,
            question_type,
            question_text,
            answer_text,
            evaluation_detail,
            evaluation_score,
            timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            job_id,
            resume_id,
            candidate_id,
            focus_area,
            question_type,
            question_text,
            answer_text,
            evaluation_detail,
            evaluation_score,
            datetime.now(UTC).isoformat(),
        ),
    )
    conn.commit()
    conn.close()


# Ensure the database exists on import
init_db()

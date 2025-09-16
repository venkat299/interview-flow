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
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS focus_area_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            candidate_id TEXT,
            focus_area TEXT,
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


def log_focus_area_response(
    focus_area: str,
    question_type: str,
    question_text: str,
    answer_text: str,
    session_id: Optional[str] = None,
    candidate_id: Optional[str] = None,
    db_path: Path = DB_PATH,
) -> None:
    """Persist focus area question/answer data for later evaluation."""

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO focus_area_logs (
            session_id, candidate_id, focus_area, question_type, question_text, answer_text, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            candidate_id,
            focus_area,
            question_type,
            question_text,
            answer_text,
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
    candidate_id: Optional[str] = None,
    db_path: Path = DB_PATH,
) -> None:
    """Persist focus area question/answer data for later evaluation."""

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO focus_area_logs (
            session_id, candidate_id, focus_area, question_type, question_text, answer_text, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            candidate_id,
            focus_area,
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

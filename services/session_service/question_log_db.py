import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional, Dict, Any

DB_PATH = Path(__file__).resolve().with_name("question_logs.db")


def _ensure_columns(cur: sqlite3.Cursor, table: str, definitions: Dict[str, str]) -> None:
    """Add any missing columns defined in ``definitions`` to ``table``."""

    cur.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cur.fetchall()}
    for column, ddl in definitions.items():
        if column not in existing:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def _normalize_score(value: Optional[Any]) -> Optional[float]:
    """Best-effort conversion of a score field to ``float``."""

    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        try:
            return float(str(value).strip())
        except (TypeError, ValueError):
            return None


def _update_focus_area_average(
    cur: sqlite3.Cursor, session_id: Optional[str], focus_area: Optional[str], score: Optional[float]
) -> None:
    """Update the running average score for a focus area within a session."""

    if not session_id or not focus_area:
        return
    score_val = _normalize_score(score)
    if score_val is None:
        return
    cur.execute(
        """
        INSERT INTO focus_area_averages (session_id, focus_area, total_score, sample_size, average_score)
        VALUES (?, ?, ?, 1, ?)
        ON CONFLICT(session_id, focus_area) DO UPDATE SET
            total_score = focus_area_averages.total_score + excluded.total_score,
            sample_size = focus_area_averages.sample_size + 1,
            average_score = (focus_area_averages.total_score + excluded.total_score)
                           / (focus_area_averages.sample_size + 1)
        """,
        (session_id, focus_area, score_val, score_val),
    )


def _update_dimension_averages(
    cur: sqlite3.Cursor,
    session_id: Optional[str],
    evaluation_type: Optional[str],
    dimensional_scores: Optional[Dict[str, Any]],
) -> None:
    """Maintain running averages for each rubric dimension per session."""

    if not session_id or not evaluation_type or not isinstance(dimensional_scores, dict):
        return
    eval_type = str(evaluation_type)
    for dimension, payload in dimensional_scores.items():
        if not isinstance(payload, dict):
            continue
        score_val = _normalize_score(payload.get("score"))
        if score_val is None:
            continue
        cur.execute(
            """
            INSERT INTO dimension_averages (
                session_id, evaluation_type, dimension_name, total_score, sample_size, average_score
            ) VALUES (?, ?, ?, ?, 1, ?)
            ON CONFLICT(session_id, evaluation_type, dimension_name) DO UPDATE SET
                total_score = dimension_averages.total_score + excluded.total_score,
                sample_size = dimension_averages.sample_size + 1,
                average_score = (dimension_averages.total_score + excluded.total_score)
                               / (dimension_averages.sample_size + 1)
            """,
            (session_id, eval_type, str(dimension), score_val, score_val),
        )


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
            evaluation_type TEXT,
            evaluation_detail TEXT,
            evaluation_score REAL,
            timestamp TEXT
        )
        """
    )
    _ensure_columns(
        cur,
        "question_logs",
        {
            "evaluation_type": "evaluation_type TEXT",
            "evaluation_detail": "evaluation_detail TEXT",
            "evaluation_score": "evaluation_score REAL",
        },
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
            evaluation_type TEXT,
            evaluation_detail TEXT,
            evaluation_score REAL,
            timestamp TEXT
        )
        """
    )
    _ensure_columns(
        cur,
        "focus_area_logs",
        {
            "evaluation_type": "evaluation_type TEXT",
            "evaluation_detail": "evaluation_detail TEXT",
            "evaluation_score": "evaluation_score REAL",
        },
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS focus_area_averages (
            session_id TEXT,
            focus_area TEXT,
            total_score REAL DEFAULT 0,
            sample_size INTEGER DEFAULT 0,
            average_score REAL DEFAULT 0,
            PRIMARY KEY (session_id, focus_area)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS dimension_averages (
            session_id TEXT,
            evaluation_type TEXT,
            dimension_name TEXT,
            total_score REAL DEFAULT 0,
            sample_size INTEGER DEFAULT 0,
            average_score REAL DEFAULT 0,
            PRIMARY KEY (session_id, evaluation_type, dimension_name)
        )
        """
    )

    conn.commit()
    conn.close()


def log_question_response(
    *,
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
    evaluation: Optional[Dict[str, Any]] = None,
    db_path: Path = DB_PATH,
) -> None:
    """Persist a single question/answer pair to the log database."""

    detail = evaluation_detail
    score = evaluation_score
    evaluation_type: Optional[str] = None
    if isinstance(evaluation, dict):
        evaluation_type = str(evaluation.get("evaluation_type") or "") or None
        if detail is None:
            detail = json.dumps(evaluation)
        score = score if score is not None else _normalize_score(
            evaluation.get("overall_score") or evaluation.get("score")
        )

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
            evaluation_type,
            evaluation_detail,
            evaluation_score,
            timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            evaluation_type,
            detail,
            score,
            datetime.now(UTC).isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def log_focus_area_response(
    *,
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
    evaluation: Optional[Dict[str, Any]] = None,
    db_path: Path = DB_PATH,
) -> None:
    """Persist focus area question/answer data for later evaluation."""

    detail = evaluation_detail
    score = evaluation_score
    evaluation_type: Optional[str] = None
    dimensional_scores: Optional[Dict[str, Any]] = None
    if isinstance(evaluation, dict):
        evaluation_type = str(evaluation.get("evaluation_type") or "") or None
        if detail is None:
            detail = json.dumps(evaluation)
        score = score if score is not None else _normalize_score(
            evaluation.get("overall_score") or evaluation.get("score")
        )
        dimensional_scores = evaluation.get("dimensional_scores")

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
            evaluation_type,
            evaluation_detail,
            evaluation_score,
            timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            evaluation_type,
            detail,
            score,
            datetime.now(UTC).isoformat(),
        ),
    )

    if evaluation_type:
        _update_dimension_averages(cur, session_id, evaluation_type, dimensional_scores)
    _update_focus_area_average(cur, session_id, focus_area, score)

    conn.commit()
    conn.close()


# Ensure the database exists on import
init_db()

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

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
            "job_id": "job_id TEXT",
            "resume_id": "resume_id TEXT",
            "candidate_id": "candidate_id TEXT",
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
            "job_id": "job_id TEXT",
            "resume_id": "resume_id TEXT",
            "candidate_id": "candidate_id TEXT",
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


def _parse_detail(detail: Optional[str]) -> Optional[Dict[str, Any]]:
    if not detail:
        return None
    try:
        return json.loads(detail)
    except Exception:
        return None


def get_focus_area_averages(
    session_id: Optional[str], db_path: Path = DB_PATH
) -> List[Dict[str, Any]]:
    """Return per-focus-area running averages for a session."""

    if not session_id:
        return []
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT focus_area, total_score, sample_size, average_score
        FROM focus_area_averages
        WHERE session_id = ?
        ORDER BY average_score DESC, focus_area ASC
        """,
        (session_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "focus_area": row[0],
            "total_score": row[1] or 0.0,
            "sample_size": row[2] or 0,
            "average_score": row[3] or 0.0,
        }
        for row in rows
    ]


def get_dimension_averages(
    session_id: Optional[str], db_path: Path = DB_PATH
) -> Dict[str, List[Dict[str, Any]]]:
    """Return rubric-dimension averages grouped by evaluation type."""

    if not session_id:
        return {}
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT evaluation_type, dimension_name, average_score, sample_size
        FROM dimension_averages
        WHERE session_id = ?
        ORDER BY evaluation_type ASC, dimension_name ASC
        """,
        (session_id,),
    )
    rows = cur.fetchall()
    conn.close()
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for etype, dimension, avg, count in rows:
        if not etype:
            continue
        grouped.setdefault(str(etype), []).append(
            {
                "dimension": str(dimension),
                "average_score": avg or 0.0,
                "sample_size": int(count or 0),
            }
        )
    return grouped


def get_session_identifiers(
    session_id: Optional[str], db_path: Path = DB_PATH
) -> Dict[str, Optional[str]]:
    """Fetch candidate/job identifiers stored alongside question logs."""

    result = {"candidate_id": None, "job_id": None, "resume_id": None}
    if not session_id:
        return result
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        for table in ("focus_area_logs", "question_logs"):
            cur.execute(
                f"""
                SELECT candidate_id, job_id, resume_id
                FROM {table}
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT 5
                """,
                (session_id,),
            )
            for cand, job, resume in cur.fetchall():
                if result["candidate_id"] in (None, "") and cand not in (None, ""):
                    result["candidate_id"] = str(cand)
                if result["job_id"] in (None, "") and job not in (None, ""):
                    result["job_id"] = str(job)
                if result["resume_id"] in (None, "") and resume not in (None, ""):
                    result["resume_id"] = str(resume)
                if all(result.values()):
                    break
            if all(result.values()):
                break
    finally:
        conn.close()
    return result


def get_session_question_logs(
    session_id: Optional[str], db_path: Path = DB_PATH
) -> List[Dict[str, Any]]:
    """Return ordered question/answer entries (with evaluations if available)."""

    if not session_id:
        return []
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            stage,
            question_type,
            question_text,
            answer_text,
            evaluation_type,
            evaluation_detail,
            evaluation_score,
            timestamp
        FROM question_logs
        WHERE session_id = ?
        ORDER BY id ASC
        """,
        (session_id,),
    )
    rows = cur.fetchall()
    conn.close()
    result: List[Dict[str, Any]] = []
    for row in rows:
        eval_payload = _parse_detail(row[5])
        result.append(
            {
                "stage": row[0],
                "question_type": row[1],
                "question_text": row[2],
                "answer_text": row[3],
                "evaluation_type": row[4],
                "evaluation_score": row[6],
                "evaluation_payload": eval_payload,
                "timestamp": row[7],
            }
        )
    return result


# Ensure the database exists on import
init_db()

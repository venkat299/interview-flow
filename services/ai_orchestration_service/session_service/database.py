import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

DB_PATH = Path(__file__).resolve().with_name("interview_sessions.db")


def init_db(db_path: Path = DB_PATH) -> None:
    """Initialize the SQLite database and create tables if they don't exist."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            start_time TEXT,
            end_time TEXT,
            blueprint TEXT,
            rubric TEXT,
            transcript TEXT,
            time_limit INTEGER,
            word_limit INTEGER,
            final_duration INTEGER,
            final_word_count INTEGER
        )
        """
    )
    # Lightweight migration: ensure newer columns exist
    cur.execute("PRAGMA table_info(sessions)")
    cols = {row[1] for row in cur.fetchall()}
    if "transcript" not in cols:
        cur.execute("ALTER TABLE sessions ADD COLUMN transcript TEXT")
    if "time_limit" not in cols:
        cur.execute("ALTER TABLE sessions ADD COLUMN time_limit INTEGER")
    if "word_limit" not in cols:
        cur.execute("ALTER TABLE sessions ADD COLUMN word_limit INTEGER")
    if "final_duration" not in cols:
        cur.execute("ALTER TABLE sessions ADD COLUMN final_duration INTEGER")
    if "final_word_count" not in cols:
        cur.execute("ALTER TABLE sessions ADD COLUMN final_word_count INTEGER")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS conversation_turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            message TEXT,
            evaluation TEXT,
            FOREIGN KEY(session_id) REFERENCES sessions(session_id)
        )
        """
    )
    conn.commit()
    conn.close()


def create_session(
    session_id: str,
    blueprint: Dict,
    time_limit: Optional[int] = None,
    word_limit: Optional[int] = None,
    db_path: Path = DB_PATH,
) -> None:
    """Create a new session entry."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO sessions (session_id, start_time, blueprint, time_limit, word_limit) VALUES (?, ?, ?, ?, ?)",
        (
            session_id,
            datetime.utcnow().isoformat(),
            json.dumps(blueprint),
            time_limit,
            word_limit,
        ),
    )
    conn.commit()
    conn.close()


def log_turn(
    session_id: str,
    role: str,
    message: str,
    evaluation: Optional[Dict] = None,
    db_path: Path = DB_PATH,
) -> None:
    """Log a conversation turn for a session."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO conversation_turns (session_id, role, message, evaluation) VALUES (?, ?, ?, ?)",
        (session_id, role, message, json.dumps(evaluation) if evaluation is not None else None),
    )
    conn.commit()
    conn.close()


def end_session(
    session_id: str,
    rubric: Optional[Dict],
    transcript: Optional[List[Dict]] = None,
    duration: Optional[int] = None,
    word_count: Optional[int] = None,
    db_path: Path = DB_PATH,
) -> None:
    """Mark a session as ended and store the final rubric and transcript."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "UPDATE sessions SET end_time = ?, rubric = ?, transcript = ?, final_duration = ?, final_word_count = ? WHERE session_id = ?",
        (
            datetime.utcnow().isoformat(),
            json.dumps(rubric) if rubric is not None else None,
            json.dumps(transcript) if transcript is not None else None,
            duration,
            word_count,
            session_id,
        ),
    )
    conn.commit()
    conn.close()


# Ensure database exists on module import
init_db()


def list_sessions(db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    """Return a list of session summaries."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT session_id, start_time, end_time FROM sessions ORDER BY start_time DESC"
    )
    rows = cur.fetchall()
    conn.close()
    return [
        {"session_id": r[0], "start_time": r[1], "end_time": r[2]}
        for r in rows
    ]


def get_session(session_id: str, db_path: Path = DB_PATH) -> Optional[Dict[str, Any]]:
    """Fetch a single session with parsed JSON fields."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT session_id, start_time, end_time, blueprint, rubric, transcript FROM sessions WHERE session_id = ?",
        (session_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    sid, start, end, blueprint, rubric, transcript = row
    def _loads(val: Optional[str]) -> Any:
        if val is None:
            return None
        try:
            return json.loads(val)
        except Exception:
            return None
    return {
        "session_id": sid,
        "start_time": start,
        "end_time": end,
        "blueprint": _loads(blueprint),
        "rubric": _loads(rubric),
        "transcript": _loads(transcript),
    }


def get_conversation_turns(session_id: str, db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    """Return all logged conversation turns for a session (evaluation parsed)."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, role, message, evaluation FROM conversation_turns WHERE session_id = ? ORDER BY id ASC",
        (session_id,),
    )
    rows = cur.fetchall()
    conn.close()
    result: List[Dict[str, Any]] = []
    for _id, role, message, evaluation in rows:
        try:
            ev = json.loads(evaluation) if evaluation is not None else None
        except Exception:
            ev = None
        result.append({"id": _id, "role": role, "message": message, "evaluation": ev})
    return result


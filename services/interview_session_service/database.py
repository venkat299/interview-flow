import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

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
            rubric TEXT
        )
        """
    )
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


def create_session(session_id: str, blueprint: Dict, db_path: Path = DB_PATH) -> None:
    """Create a new session entry."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO sessions (session_id, start_time, blueprint) VALUES (?, ?, ?)",
        (session_id, datetime.utcnow().isoformat(), json.dumps(blueprint)),
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


def end_session(session_id: str, rubric: Optional[Dict], db_path: Path = DB_PATH) -> None:
    """Mark a session as ended and store the final rubric."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "UPDATE sessions SET end_time = ?, rubric = ? WHERE session_id = ?",
        (datetime.utcnow().isoformat(), json.dumps(rubric) if rubric is not None else None, session_id),
    )
    conn.commit()
    conn.close()


# Ensure database exists on module import
init_db()

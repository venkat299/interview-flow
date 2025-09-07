import os
import sqlite3
from typing import Dict, List, Optional

from gateway_service.config import settings


def _ensure_dir(path: str) -> None:
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    """Open a connection to the samples SQLite database, creating it if needed."""
    db_path = settings.samples_db_path
    if not os.path.isabs(db_path):
        base_dir = os.path.dirname(__file__)
        db_path = os.path.join(base_dir, db_path)
    _ensure_dir(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS samples (
                key TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                job_description TEXT NOT NULL,
                resume TEXT NOT NULL
            )
            """
        )
        conn.commit()


def seed_if_empty() -> None:
    with get_connection() as conn:
        cur = conn.execute("SELECT COUNT(1) AS c FROM samples")
        count = cur.fetchone()[0]
        if count:
            return
        rows = [
            (
                "frontend",
                "Frontend Developer",
                "We are looking for a frontend developer proficient in HTML, CSS, and JavaScript.",
                "Experienced frontend engineer with a focus on building responsive web interfaces.",
            ),
            (
                "data",
                "Data Scientist",
                "Seeking a data scientist with expertise in Python and machine learning.",
                "Data scientist skilled in statistical modeling and data visualization. Data science, machine learning",
            ),
        ]
        conn.executemany(
            "INSERT OR REPLACE INTO samples(key, title, job_description, resume) VALUES(?,?,?,?)",
            rows,
        )
        conn.commit()


def list_samples() -> List[Dict[str, str]]:
    with get_connection() as conn:
        cur = conn.execute("SELECT key, title FROM samples ORDER BY title")
        return [{"key": r["key"], "title": r["title"]} for r in cur.fetchall()]


def get_sample(key: str) -> Optional[Dict[str, str]]:
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT key, title, job_description, resume FROM samples WHERE key = ?",
            (key,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "key": row["key"],
            "title": row["title"],
            "job_description": row["job_description"],
            "resume": row["resume"],
        }

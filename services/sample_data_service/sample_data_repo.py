import json
import os
import sqlite3
from typing import Any, Dict, Iterable, List, Optional

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
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create required tables if they do not already exist."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS job_postings (
                id INTEGER PRIMARY KEY,
                job_title TEXT NOT NULL,
                company TEXT,
                location TEXT,
                experience_level TEXT,
                category TEXT,
                description TEXT,
                responsibilities TEXT,
                required_qualifications TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS candidate_resumes (
                candidate_id TEXT PRIMARY KEY,
                resume TEXT NOT NULL,
                job_id INTEGER NOT NULL,
                display_name TEXT,
                FOREIGN KEY(job_id) REFERENCES job_postings(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS candidates (
                candidate_id TEXT PRIMARY KEY,
                job_id INTEGER NOT NULL,
                profile TEXT NOT NULL,
                resume TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES job_postings(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS candidate_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id TEXT NOT NULL,
                job_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                FOREIGN KEY(candidate_id) REFERENCES candidates(candidate_id),
                FOREIGN KEY(job_id) REFERENCES job_postings(id)
            )
            """
        )
        # Ensure optional columns exist without clobbering existing data
        cur = conn.execute("PRAGMA table_info(candidate_resumes)")
        columns = {row["name"] for row in cur.fetchall()}
        if "display_name" not in columns:
            conn.execute("ALTER TABLE candidate_resumes ADD COLUMN display_name TEXT")
        conn.commit()


def seed_if_empty() -> None:
    """Populate the job_postings table with seed data if empty."""
    with get_connection() as conn:
        cur = conn.execute("SELECT COUNT(1) AS c FROM job_postings")
        count = cur.fetchone()[0]
        if count:
            return
        data_file = os.path.join(os.path.dirname(__file__), "data", "job_postings.json")
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        rows = []
        for posting in data.get("job_postings", []):
            rows.append(
                (
                    posting["id"],
                    posting["job_title"],
                    posting.get("company"),
                    posting.get("location"),
                    posting.get("experience_level"),
                    posting.get("category"),
                    posting.get("description"),
                    json.dumps(posting.get("responsibilities", [])),
                    json.dumps(posting.get("required_qualifications", [])),
                )
            )
        conn.executemany(
            """
            INSERT INTO job_postings(
                id, job_title, company, location, experience_level,
                category, description, responsibilities, required_qualifications
            ) VALUES (?,?,?,?,?,?,?,?,?)
            """,
            rows,
        )
        conn.commit()


def list_job_postings() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.execute("SELECT id, job_title FROM job_postings ORDER BY id")
        return [{"id": r["id"], "job_title": r["job_title"]} for r in cur.fetchall()]


def create_job_posting(
    job_title: str,
    *,
    company: Optional[str] = None,
    location: Optional[str] = None,
    experience_level: Optional[str] = None,
    category: Optional[str] = None,
    description: Optional[str] = None,
    responsibilities: Optional[Iterable[str]] = None,
    required_qualifications: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    if not job_title:
        raise ValueError("Job title is required")

    def _normalize(values: Optional[Iterable[str]]) -> List[str]:
        if values is None:
            return []
        if isinstance(values, str):
            return [line.strip() for line in values.splitlines() if line.strip()]
        normalized: List[str] = []
        for item in values:
            text = str(item or "").strip()
            if text:
                normalized.append(text)
        return normalized

    responsibilities_list = _normalize(responsibilities)
    qualifications_list = _normalize(required_qualifications)
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO job_postings(
                job_title, company, location, experience_level, category,
                description, responsibilities, required_qualifications
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                job_title.strip(),
                (company or "").strip() or None,
                (location or "").strip() or None,
                (experience_level or "").strip() or None,
                (category or "").strip() or None,
                (description or "").strip(),
                json.dumps(responsibilities_list),
                json.dumps(qualifications_list),
            ),
        )
        conn.commit()
        new_id = cur.lastrowid
    item = get_job_posting(new_id)
    if not item:
        raise ValueError("Failed to create job posting")
    return item


def delete_job_posting(job_id: int) -> bool:
    with get_connection() as conn:
        conn.execute("DELETE FROM candidate_sessions WHERE job_id = ?", (job_id,))
        conn.execute("DELETE FROM candidate_resumes WHERE job_id = ?", (job_id,))
        conn.execute("DELETE FROM candidates WHERE job_id = ?", (job_id,))
        cur = conn.execute("DELETE FROM job_postings WHERE id = ?", (job_id,))
        conn.commit()
        return cur.rowcount > 0


def get_job_posting(job_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT id, job_title, company, location, experience_level, category,
                   description, responsibilities, required_qualifications
            FROM job_postings WHERE id = ?
            """,
            (job_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "job_title": row["job_title"],
            "company": row["company"],
            "location": row["location"],
            "experience_level": row["experience_level"],
            "category": row["category"],
            "description": row["description"],
            "responsibilities": json.loads(row["responsibilities"] or "[]"),
            "required_qualifications": json.loads(row["required_qualifications"] or "[]"),
        }


def upsert_candidate_resume(
    candidate_id: str,
    resume: str,
    job_id: int,
    display_name: Optional[str] = None,
) -> None:
    if not candidate_id:
        raise ValueError("candidate_id is required")
    if job_id is None:
        raise ValueError("job_id is required")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO candidate_resumes(candidate_id, resume, job_id, display_name)
            VALUES(?,?,?,?)
            ON CONFLICT(candidate_id) DO UPDATE SET
                resume = excluded.resume,
                job_id = excluded.job_id,
                display_name = COALESCE(excluded.display_name, candidate_resumes.display_name)
            """,
            (candidate_id, resume, job_id, display_name),
        )
        conn.commit()


def list_candidate_resumes() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT
                cr.candidate_id,
                cr.job_id,
                COALESCE(cr.display_name, cr.candidate_id) AS display_name,
                jp.job_title
            FROM candidate_resumes cr
            LEFT JOIN job_postings jp ON cr.job_id = jp.id
            ORDER BY display_name COLLATE NOCASE
            """
        )
        return [
            {
                "candidate_id": row["candidate_id"],
                "job_id": row["job_id"],
                "display_name": row["display_name"],
                "job_title": row["job_title"],
            }
            for row in cur.fetchall()
        ]


def get_candidate_resume(candidate_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT candidate_id, resume, job_id, display_name FROM candidate_resumes WHERE candidate_id = ?",
            (candidate_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "candidate_id": row["candidate_id"],
            "resume": row["resume"],
            "job_id": row["job_id"],
            "display_name": row["display_name"],
        }


def upsert_candidate(candidate_id: str, job_id: int, profile: str, resume: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO candidates(candidate_id, job_id, profile, resume)
            VALUES(?,?,?,?)
            """,
            (candidate_id, job_id, profile, resume),
        )
        conn.commit()


def get_candidate(candidate_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT candidate_id, job_id, profile, resume FROM candidates WHERE candidate_id = ?",
            (candidate_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "candidate_id": row["candidate_id"],
            "job_id": row["job_id"],
            "profile": row["profile"],
            "resume": row["resume"],
        }


def link_candidate_session(candidate_id: str, job_id: int, session_id: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO candidate_sessions(candidate_id, job_id, session_id)
            VALUES(?,?,?)
            """,
            (candidate_id, job_id, session_id),
        )
        conn.commit()


def delete_candidate_resume(candidate_id: str) -> bool:
    with get_connection() as conn:
        conn.execute("DELETE FROM candidate_sessions WHERE candidate_id = ?", (candidate_id,))
        conn.execute("DELETE FROM candidates WHERE candidate_id = ?", (candidate_id,))
        cur = conn.execute(
            "DELETE FROM candidate_resumes WHERE candidate_id = ?",
            (candidate_id,),
        )
        conn.commit()
        return cur.rowcount > 0

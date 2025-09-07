import json
import os
import sqlite3
from typing import Any, Dict, List, Optional

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
                FOREIGN KEY(job_id) REFERENCES job_postings(id)
            )
            """
        )
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


def upsert_candidate_resume(candidate_id: str, resume: str, job_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO candidate_resumes(candidate_id, resume, job_id)
            VALUES(?,?,?)
            """,
            (candidate_id, resume, job_id),
        )
        conn.commit()


def get_candidate_resume(candidate_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT candidate_id, resume, job_id FROM candidate_resumes WHERE candidate_id = ?",
            (candidate_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "candidate_id": row["candidate_id"],
            "resume": row["resume"],
            "job_id": row["job_id"],
        }

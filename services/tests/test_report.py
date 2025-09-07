from pathlib import Path

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

from api_service.app.main import app
from session_service import database as db


@pytest.fixture
def client():
    return TestClient(app)


def test_report_endpoint(monkeypatch, tmp_path: Path, client):
    tmp_db = tmp_path / "sessions.db"
    db.init_db(tmp_db)
    session_id = "sess-test"
    blueprint = {
        "topics": [
            {
                "name": "python",
                "relevance_to_role": 10,
                "required_depth": "Advanced",
                "jd_context": ["python"],
                "resume_evidence": ["python exp"],
            }
        ]
    }
    db.create_session(session_id, blueprint, db_path=tmp_db)
    eval_data = {
        "score": 8,
        "assessed_depth": "Advanced",
        "llm_confidence": "High",
        "justification": "Good",
        "is_truthful": True,
        "topic": "python",
        "difficulty": 3,
    }
    db.log_turn(session_id, "interviewer", "What is Python?", db_path=tmp_db)
    db.log_turn(session_id, "candidate", "A language", eval_data, db_path=tmp_db)
    db.end_session(
        session_id,
        rubric={"performance_log": [eval_data]},
        transcript=[{"role": "interviewer", "message": "What is Python?"}, {"role": "candidate", "message": "A language"}],
        final_score=8.0,
        summary="Great",
        db_path=tmp_db,
    )

    import api_service.app.main as app_main

    monkeypatch.setattr(app_main, "db_get_session", lambda sid: db.get_session(sid, db_path=tmp_db))
    monkeypatch.setattr(app_main, "db_get_turns", lambda sid: db.get_conversation_turns(sid, db_path=tmp_db))

    resp = client.get(f"/api/v1/sessions/{session_id}/report")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 100

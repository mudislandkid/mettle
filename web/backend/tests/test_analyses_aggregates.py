"""Tests for GET /api/analysis/ enriched aggregate fields."""

import importlib
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session


def test_list_analyses_includes_avg_health_and_secrets(security_env, tmp_path):
    security_env()
    from web.backend import main as backend_main

    importlib.reload(backend_main)
    from web.backend.database.connection import engine, run_migrations
    from web.backend.database.models import Analysis, Project

    run_migrations()
    client = TestClient(backend_main.app)

    # Wipe shared DB state (Phase B+C integration test pattern)
    with Session(engine) as session:
        session.exec(text("DELETE FROM projects"))
        session.exec(text("DELETE FROM analyses"))
        session.commit()

    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        a = Analysis(
            directory_path="/code",
            analyzed_at=now - timedelta(hours=1),
            completed_at=(now - timedelta(hours=1)) + timedelta(seconds=47),
            status="completed",
        )
        session.add(a)
        session.commit()
        session.refresh(a)
        # 2 projects with 2 secrets + 1 secret = 3 total
        session.add(
            Project(
                analysis_id=a.id,
                name="p1",
                path="/code/p1",
                secrets_found=2,
                code_lines=100,
                total_lines=100,
            )
        )
        session.add(
            Project(
                analysis_id=a.id,
                name="p2",
                path="/code/p2",
                secrets_found=1,
                code_lines=200,
                total_lines=200,
            )
        )
        session.commit()

    r = client.get("/api/analysis/?limit=20")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body) == 1
    row = body[0]
    assert row["secrets_found"] == 3
    assert "avg_health" in row
    assert "duration_seconds" in row
    assert row["duration_seconds"] == 47


def test_list_analyses_running_has_null_duration(security_env, tmp_path):
    """A running analysis has no completed_at — duration is None."""
    security_env()
    from web.backend import main as backend_main

    importlib.reload(backend_main)
    from web.backend.database.connection import engine, run_migrations
    from web.backend.database.models import Analysis

    run_migrations()
    client = TestClient(backend_main.app)

    with Session(engine) as session:
        session.exec(text("DELETE FROM projects"))
        session.exec(text("DELETE FROM analyses"))
        session.commit()
        a = Analysis(directory_path="/code", status="running")
        session.add(a)
        session.commit()

    r = client.get("/api/analysis/?limit=20")
    body = r.json()
    assert len(body) == 1
    row = body[0]
    assert row["status"] == "running"
    assert row["duration_seconds"] is None
    assert row["secrets_found"] == 0

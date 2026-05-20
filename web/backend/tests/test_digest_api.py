"""Integration test for GET /api/digest/."""

import importlib
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlmodel import Session


def test_digest_endpoint_returns_seven_sections(security_env, tmp_path):
    """GET /api/digest/?since=7d returns all 7 sections in fixed order."""
    security_env()
    from web.backend import main as backend_main

    importlib.reload(backend_main)
    from web.backend.database.connection import engine, run_migrations
    from web.backend.database.models import Analysis, Project

    run_migrations()
    client = TestClient(backend_main.app)

    # Wipe any stale rows from prior test runs so counts are deterministic.
    from sqlmodel import delete as sql_delete

    with Session(engine) as session:
        session.exec(sql_delete(Project))
        session.exec(sql_delete(Analysis))
        session.commit()

    # Seed: one project with two analyses across the window boundary
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        old = Analysis(
            directory_path="/p", analyzed_at=now - timedelta(days=10), status="completed"
        )
        session.add(old)
        session.commit()
        session.refresh(old)
        session.add(
            Project(analysis_id=old.id, name="p", path="/p", code_lines=100, total_lines=100)
        )
        session.commit()
        new = Analysis(
            directory_path="/p", analyzed_at=now - timedelta(hours=1), status="completed"
        )
        session.add(new)
        session.commit()
        session.refresh(new)
        session.add(
            Project(analysis_id=new.id, name="p", path="/p", code_lines=250, total_lines=250)
        )
        session.commit()

    r = client.get("/api/digest/?since=7d&top=5&stale_days=30")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["sections"]) == 7
    kinds = [s["kind"] for s in body["sections"]]
    assert kinds == [
        "grown_most",
        "biggest_swing",
        "dependency_drift",
        "stalled_with_todos",
        "newly_stale",
        "new_since",
        "no_recent_activity",
    ]
    assert body["total_projects"] == 1
    assert body["projects_with_baseline"] == 1

    # Grown the most should have the planted +150 entry
    grown = next(s for s in body["sections"] if s["kind"] == "grown_most")
    assert len(grown["entries"]) == 1
    assert grown["entries"][0]["headline_value"] == 150

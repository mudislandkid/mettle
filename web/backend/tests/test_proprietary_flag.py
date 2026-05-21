"""Tests for the `proprietary` project flag (ENHANCEMENTS #25).

The flag suppresses the "Missing license" risk signal for projects that are
closed-source by design. These tests pin the wiring on the backend: the flag
is registered in the constants and round-trips through the bulk-flags endpoint.
"""

import importlib

from fastapi.testclient import TestClient
from sqlmodel import Session


def test_proprietary_is_registered_in_flag_constants():
    """The new flag is present in all three constants so the API and the
    frontend's `/flags/types` lookup both see it."""
    from web.backend.database.models import FLAG_COLORS, FLAG_LABELS, FLAG_TYPES

    assert "proprietary" in FLAG_TYPES
    assert FLAG_LABELS["proprietary"] == "Proprietary"
    assert FLAG_COLORS["proprietary"].startswith("#")


def test_proprietary_round_trips_through_bulk_flags(security_env, tmp_path):
    """POST /api/projects/bulk/flags with `proprietary` succeeds and the flag
    appears on the project's flags list afterwards."""
    security_env()
    from web.backend import main as backend_main

    importlib.reload(backend_main)
    from web.backend.database.connection import engine, run_migrations
    from web.backend.database.models import Analysis, Project

    run_migrations()
    client = TestClient(backend_main.app)

    with Session(engine) as session:
        analysis = Analysis(directory_path=str(tmp_path))
        session.add(analysis)
        session.commit()
        session.refresh(analysis)

        project = Project(name="closed-src", path=str(tmp_path), analysis_id=analysis.id)
        session.add(project)
        session.commit()
        session.refresh(project)
        pid = project.id

    r = client.post(
        "/api/projects/bulk/flags",
        json={"project_ids": [pid], "operation": "add", "flags": ["proprietary"]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["updated"] == 1
    assert body["project_ids"] == [pid]

    # Confirm the flag is now visible on the project response.
    detail = client.get(f"/api/projects/{pid}").json()
    assert "proprietary" in detail["flags"]

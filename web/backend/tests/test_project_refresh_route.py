"""Error mapping for POST /api/projects/{id}/refresh.

The handler wraps the whole re-analysis in `try/except Exception`, which also
catches the `HTTPException`s it raises itself — so a legitimate 4xx ("path no
longer exists", "nothing analyzable here") used to reach the client as a
generic 500 "Re-analysis failed (see server logs)". These tests pin the
intended status codes.
"""

import importlib

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session


@pytest.fixture
def client_and_engine(security_env):
    security_env()
    from web.backend import main as backend_main

    importlib.reload(backend_main)
    from web.backend.database.connection import engine, run_migrations

    run_migrations()
    return TestClient(backend_main.app), engine


def _make_project(engine, path: str) -> int:
    from web.backend.database.models import Analysis, Project

    with Session(engine) as session:
        analysis = Analysis(directory_path=path, status="completed")
        session.add(analysis)
        session.commit()
        session.refresh(analysis)

        project = Project(analysis_id=analysis.id, name="empty", path=path)
        session.add(project)
        session.commit()
        session.refresh(project)
        return project.id


def test_refresh_empty_project_returns_400_not_500(client_and_engine, tmp_path):
    """An empty directory is a client-side problem, not a server error."""
    client, engine = client_and_engine
    empty = tmp_path / "nothing-here"
    empty.mkdir()
    project_id = _make_project(engine, str(empty))

    response = client.post(f"/api/projects/{project_id}/refresh")

    assert response.status_code == 400
    assert "Failed to analyze" in response.json()["detail"]


def test_refresh_missing_path_returns_400(client_and_engine, tmp_path):
    """A deleted project directory must keep its 400, not become a 500."""
    client, engine = client_and_engine
    gone = tmp_path / "deleted"
    project_id = _make_project(engine, str(gone))

    response = client.post(f"/api/projects/{project_id}/refresh")

    assert response.status_code == 400
    assert "no longer exists" in response.json()["detail"]


def test_refresh_unknown_project_returns_404(client_and_engine):
    client, _ = client_and_engine
    assert client.post("/api/projects/999999/refresh").status_code == 404

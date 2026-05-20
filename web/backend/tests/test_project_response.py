"""Tests confirming ProjectResponse surfaces the new scanner fields."""

import importlib

from fastapi.testclient import TestClient
from sqlmodel import Session


def test_project_response_includes_scanner_fields(security_env, tmp_path):
    """A Project row with scanner output gets serialised through ProjectResponse."""
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

        project = Project(
            name="demo",
            path=str(tmp_path),
            analysis_id=analysis.id,
            secrets_found=2,
            secrets_detail=[
                {
                    "file": "src/x.py",
                    "line": 5,
                    "kind": "aws_access_key_id",
                    "snippet_hash": "abcdef0123456789",
                    "severity": "high",
                }
            ],
            license_spdx="MIT",
        )
        session.add(project)
        session.commit()
        session.refresh(project)
        pid = project.id

    r = client.get(f"/api/projects/{pid}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["secrets_found"] == 2
    assert body["license_spdx"] == "MIT"
    assert isinstance(body["secrets_detail"], list)
    assert body["secrets_detail"][0]["kind"] == "aws_access_key_id"

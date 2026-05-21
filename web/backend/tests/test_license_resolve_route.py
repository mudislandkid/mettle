"""Integration test for POST /api/projects/{id}/resolve-licenses.

The resolver façade is monkeypatched to avoid network — the test is about
wiring (route → resolver → DB write → response includes new fields), not
about the resolver internals (covered in mettle/tests/).
"""

import importlib

from fastapi.testclient import TestClient
from sqlmodel import Session


def test_resolve_licenses_writes_back_and_sets_risk(security_env, tmp_path, monkeypatch):
    security_env()
    from web.backend import main as backend_main

    importlib.reload(backend_main)
    from web.backend.database.connection import engine, run_migrations
    from web.backend.database.models import Analysis, Project, ProjectFlag

    run_migrations()
    client = TestClient(backend_main.app)

    # Stub the resolver so the route exercises serialisation, not the net.
    def fake_resolve_project(deps, *, project_license_spdx, project_flags, **_):
        licenses = [
            {
                "name": "react",
                "version": "18.2.0",
                "manager": "npm",
                "spdx": "MIT",
                "source": "npm",
            },
            {
                "name": "gpl-thing",
                "version": "1.0",
                "manager": "npm",
                "spdx": "GPL-3.0-only",
                "source": "npm",
            },
        ]
        summary = {
            "resolved": 2,
            "unresolved": 0,
            "by_spdx": {"MIT": 1, "GPL-3.0-only": 1},
            "copyleft_strong": 1,
            "copyleft_weak": 0,
        }
        has_risk = "proprietary" in (project_flags or []) or project_license_spdx is None
        return licenses, summary, has_risk and summary["copyleft_strong"] > 0

    monkeypatch.setattr("mettle.license_resolver.runner.resolve_project", fake_resolve_project)

    with Session(engine) as session:
        analysis = Analysis(directory_path=str(tmp_path))
        session.add(analysis)
        session.commit()
        session.refresh(analysis)

        project = Project(
            name="closed-src",
            path=str(tmp_path),
            analysis_id=analysis.id,
            dependencies=[
                {"name": "react", "version": "18.2.0", "manager": "npm"},
                {"name": "gpl-thing", "version": "1.0", "manager": "npm"},
            ],
        )
        session.add(project)
        session.commit()
        session.refresh(project)
        pid = project.id
        session.add(ProjectFlag(project_id=pid, flag_type="proprietary"))
        session.commit()

    r = client.post(f"/api/projects/{pid}/resolve-licenses")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["dependency_license_summary"]["resolved"] == 2
    assert body["dependency_license_summary"]["copyleft_strong"] == 1
    assert body["has_license_risk"] is True
    assert len(body["dependency_licenses"]) == 2
    assert any(d["spdx"] == "GPL-3.0-only" for d in body["dependency_licenses"])


def test_resolve_licenses_404_for_unknown_project(security_env):
    security_env()
    from web.backend import main as backend_main

    importlib.reload(backend_main)
    from web.backend.database.connection import run_migrations

    run_migrations()
    client = TestClient(backend_main.app)
    r = client.post("/api/projects/999999/resolve-licenses")
    assert r.status_code == 404

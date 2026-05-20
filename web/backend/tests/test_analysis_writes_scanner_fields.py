"""Regression test: scanner fields must be persisted to the DB when the
analysis background task writes Project rows. The bug caught by the final
review of Phase C: routes_analysis.py was constructing Project() without
passing the three new scanner fields, so values silently dropped to defaults.
"""

import importlib
import time

from fastapi.testclient import TestClient
from sqlmodel import Session, select


def test_planted_secret_is_persisted_via_analysis_pipeline(security_env, tmp_path):
    """End-to-end: a planted secret in a project under METTLE_SCAN_ROOTS must
    surface as secrets_found>0 on the persisted Project row."""
    # Set up a fake parent dir with one project containing a planted AKIA key
    # and a MIT LICENSE.
    parent = tmp_path / "code"
    parent.mkdir()
    project = parent / "myapp"
    project.mkdir()
    (project / "config.py").write_text('AWS_KEY = "AKIAIOSFODNN7EXAMPLE"\n')
    from mettle.license_corpus import SPDX_CORPUS

    (project / "LICENSE").write_text(SPDX_CORPUS["MIT"])

    security_env(SCAN_ROOTS=str(parent))

    import web.backend.main as backend_main

    importlib.reload(backend_main)
    from web.backend.database.connection import engine, run_migrations
    from web.backend.database.models import Project

    run_migrations()
    client = TestClient(backend_main.app)

    # POST /api/analysis/start — route is @router.post("/start") mounted at
    # prefix="/api/analysis" (verified via grep in routes_analysis.py + main.py).
    response = client.post(
        "/api/analysis/start",
        json={"directory_path": str(parent)},
    )
    assert response.status_code in (
        200,
        201,
        202,
    ), f"start failed: {response.status_code} {response.text}"
    body = response.json()
    # The route returns {"id": ..., "status": "pending"}
    analysis_id = body.get("id") or body.get("analysis_id")
    assert analysis_id is not None, f"no id in response: {body}"

    # The analysis runs in a background task.  TestClient typically runs
    # background tasks synchronously, but poll briefly to be safe.
    for _ in range(30):  # up to 3 seconds
        with Session(engine) as session:
            projects = session.exec(select(Project).where(Project.analysis_id == analysis_id)).all()
            if projects:
                break
        time.sleep(0.1)

    with Session(engine) as session:
        projects = session.exec(select(Project).where(Project.analysis_id == analysis_id)).all()

    assert len(projects) == 1, f"expected 1 project, got {len(projects)}"
    p = projects[0]
    assert p.name == "myapp"
    assert p.secrets_found == 1, f"secrets_found should be 1, got {p.secrets_found}"
    assert p.license_spdx == "MIT", f"license_spdx should be MIT, got {p.license_spdx}"
    assert p.secrets_detail is not None, "secrets_detail should not be None"
    assert p.secrets_detail[0]["kind"] == "aws_access_key_id"

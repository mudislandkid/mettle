"""Tests for security.path_jail — METTLE_SCAN_ROOTS enforcement."""

import pytest

from web.backend.security import path_jail


def test_unset_roots_returns_resolved_path_no_check(security_env, tmp_path):
    security_env()  # METTLE_SCAN_ROOTS unset
    result = path_jail.resolve_and_check(str(tmp_path / "anywhere"))
    assert result == (tmp_path / "anywhere").resolve()


def test_empty_roots_treated_as_unset(security_env, tmp_path):
    security_env(SCAN_ROOTS="   ")
    result = path_jail.resolve_and_check(str(tmp_path / "anywhere"))
    assert result == (tmp_path / "anywhere").resolve()


def test_abs_inside_root_returns_resolved(security_env, tmp_path):
    root = tmp_path / "allowed"
    root.mkdir()
    (root / "sub").mkdir()
    security_env(SCAN_ROOTS=str(root))
    result = path_jail.resolve_and_check(str(root / "sub"))
    assert result == (root / "sub").resolve()


def test_abs_outside_roots_raises(security_env, tmp_path):
    root = tmp_path / "allowed"
    root.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    security_env(SCAN_ROOTS=str(root))
    with pytest.raises(path_jail.PathJailError):
        path_jail.resolve_and_check(str(elsewhere))


def test_dotdot_escape_caught_after_resolve(security_env, tmp_path):
    root = tmp_path / "allowed"
    root.mkdir()
    security_env(SCAN_ROOTS=str(root))
    with pytest.raises(path_jail.PathJailError):
        path_jail.resolve_and_check(f"{root}/../elsewhere")


def test_symlink_into_root_allowed(security_env, tmp_path):
    root = tmp_path / "allowed"
    root.mkdir()
    target = root / "real"
    target.mkdir()
    link = root / "link"
    link.symlink_to(target)
    security_env(SCAN_ROOTS=str(root))
    # link resolves to root/real which is inside root — allowed
    result = path_jail.resolve_and_check(str(link))
    assert result == target.resolve()


def test_symlink_out_of_root_rejected(security_env, tmp_path):
    root = tmp_path / "allowed"
    root.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    link = root / "escape"
    link.symlink_to(elsewhere)
    security_env(SCAN_ROOTS=str(root))
    # link resolves to elsewhere/ which is OUTSIDE root — rejected
    with pytest.raises(path_jail.PathJailError):
        path_jail.resolve_and_check(str(link))


def test_filter_jailed_drops_violators_silently(security_env, tmp_path):
    root = tmp_path / "allowed"
    root.mkdir()
    inside = root / "ok"
    inside.mkdir()
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    security_env(SCAN_ROOTS=str(root))
    survivors = path_jail.filter_jailed([str(inside), str(outside)])
    assert inside.resolve() in survivors
    assert outside.resolve() not in survivors


def test_validate_path_returns_403_for_escape(security_env, tmp_path):
    """The real /api/validate-path route enforces the jail."""
    root = tmp_path / "allowed"
    root.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    security_env(SCAN_ROOTS=str(root))

    import importlib

    from web.backend import main as backend_main

    importlib.reload(backend_main)
    from fastapi.testclient import TestClient

    client = TestClient(backend_main.app)
    r = client.post("/api/validate-path", json={"path": str(elsewhere)})
    assert r.status_code == 403


def test_validate_path_returns_200_inside_root(security_env, tmp_path):
    root = tmp_path / "allowed"
    root.mkdir()
    inside = root / "ok"
    inside.mkdir()
    security_env(SCAN_ROOTS=str(root))

    import importlib

    from web.backend import main as backend_main

    importlib.reload(backend_main)
    from fastapi.testclient import TestClient

    client = TestClient(backend_main.app)
    r = client.post("/api/validate-path", json={"path": str(inside)})
    assert r.status_code == 200


def test_git_stats_returns_403_for_db_path_outside_roots(security_env, tmp_path):
    """The /api/projects/{id}/git/stats route enforces the jail on the DB-stored path."""
    root = tmp_path / "allowed"
    root.mkdir()
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    security_env(SCAN_ROOTS=str(root))

    import importlib

    from web.backend import main as backend_main

    importlib.reload(backend_main)
    from fastapi.testclient import TestClient
    from sqlmodel import Session

    client = TestClient(backend_main.app)

    # Seed an Analysis row first (Project.analysis_id is non-nullable).
    from web.backend.database.connection import engine
    from web.backend.database.models import Analysis, Project

    with Session(engine) as session:
        analysis = Analysis(directory_path=str(outside))
        session.add(analysis)
        session.commit()
        session.refresh(analysis)

        project = Project(
            name="outside-project",
            path=str(outside),
            analysis_id=analysis.id,
        )
        session.add(project)
        session.commit()
        session.refresh(project)
        project_id = project.id

    r = client.get(f"/api/projects/{project_id}/git/stats")
    assert r.status_code == 403, r.text

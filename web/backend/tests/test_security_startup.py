"""Tests for security.startup — one-shot process-aborting gates."""

import pytest

from web.backend.security import startup


def test_loopback_bind_always_safe(security_env):
    security_env()  # no token
    startup.assert_bind_is_safe("127.0.0.1", allow_public=False)
    startup.assert_bind_is_safe("localhost", allow_public=False)
    startup.assert_bind_is_safe("::1", allow_public=False)
    # No SystemExit raised — pass.


def test_public_bind_without_flag_exits(security_env):
    security_env()
    with pytest.raises(SystemExit) as exc:
        startup.assert_bind_is_safe("0.0.0.0", allow_public=False)
    assert "--allow-public-bind" in str(exc.value)


def test_public_bind_without_token_exits(security_env):
    security_env()  # METTLE_TOKEN unset
    with pytest.raises(SystemExit) as exc:
        startup.assert_bind_is_safe("0.0.0.0", allow_public=True)
    assert "METTLE_TOKEN" in str(exc.value)


def test_public_bind_with_token_and_flag_passes(security_env):
    security_env(TOKEN="abc")
    startup.assert_bind_is_safe("0.0.0.0", allow_public=True)
    # No raise — pass.


def test_validate_cors_rejects_wildcard(security_env):
    security_env()
    with pytest.raises(SystemExit) as exc:
        startup.validate_cors(["*"])
    assert "wildcard" in str(exc.value).lower()


def test_validate_cors_rejects_missing_scheme(security_env):
    security_env()
    with pytest.raises(SystemExit) as exc:
        startup.validate_cors(["example.com"])
    assert "scheme" in str(exc.value).lower()


def test_validate_cors_rejects_empty_with_token(security_env):
    security_env(TOKEN="abc")
    with pytest.raises(SystemExit) as exc:
        startup.validate_cors([])
    assert "empty" in str(exc.value).lower() or "no allowed origins" in str(exc.value).lower()


def test_run_py_main_refuses_public_bind_without_flag(security_env, capsys):
    """Smoke test that web/run.py main() calls assert_bind_is_safe."""
    import argparse
    import sys

    security_env()
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3] / "web"))
    try:
        import run as web_run
    finally:
        sys.path.pop(0)

    ns = argparse.Namespace(
        mode="backend-only",
        backend_host="0.0.0.0",
        backend_port=8000,
        frontend_port=5173,
        skip_install=True,
        auto_install=False,
        allow_public_bind=False,
    )
    with pytest.raises(SystemExit) as exc:
        web_run.main(ns)
    assert "--allow-public-bind" in str(exc.value)

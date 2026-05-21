"""Shared pytest fixtures for the web/backend test suite.

The `security_env` fixture is the main one — sets METTLE_* env vars in a
single call and clears settings caches between tests so the lru_cache'd
loader functions actually see the new values.
"""

import os
import tempfile
from pathlib import Path

# Route every test to a tmp SQLite DB BEFORE any test module imports
# web.backend.database.connection (which reads DATABASE_URL once, at import).
# Without this, tests that POST /api/analysis/start scribble pytest tmpdir
# paths into the dev mettle.db's recent_paths / analyses tables.
_TEST_DB_DIR = Path(tempfile.mkdtemp(prefix="mettle-test-"))
_TEST_DB_PATH = _TEST_DB_DIR / "test.db"
os.environ.setdefault("METTLE_DATABASE_URL", f"sqlite:///{_TEST_DB_PATH}")

import pytest  # noqa: E402


@pytest.fixture
def security_env(monkeypatch):
    """Set + clear METTLE_* env vars cleanly across tests.

    Usage:
        def test_x(security_env):
            security_env(TOKEN="abc", SCAN_ROOTS="/tmp")
            # ... assertions
    """
    from web.backend.security import settings

    def _apply(**kw):
        for name in ("TOKEN", "CORS_ORIGINS", "SCAN_ROOTS", "DEBUG"):
            monkeypatch.delenv(f"METTLE_{name}", raising=False)
        for k, v in kw.items():
            monkeypatch.setenv(f"METTLE_{k.upper()}", v)
        settings._cache_clear()

    settings._cache_clear()
    yield _apply
    settings._cache_clear()

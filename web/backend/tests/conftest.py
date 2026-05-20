"""Shared pytest fixtures for the web/backend test suite.

The `security_env` fixture is the main one — sets METTLE_* env vars in a
single call and clears settings caches between tests so the lru_cache'd
loader functions actually see the new values.
"""

import pytest


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

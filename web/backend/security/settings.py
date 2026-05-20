"""Single source of truth for METTLE_* security env vars.

Every other security module imports from here. Functions are cached via
@lru_cache so test code can monkeypatch env vars and call `_cache_clear()`
to reset between cases.
"""

import os
from functools import lru_cache
from pathlib import Path

DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://localhost:8000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8000",
)


@lru_cache(maxsize=1)
def token() -> str | None:
    """Return METTLE_TOKEN or None if unset/blank."""
    raw = os.environ.get("METTLE_TOKEN", "").strip()
    return raw or None


@lru_cache(maxsize=1)
def cors_origins() -> list[str]:
    """Return parsed METTLE_CORS_ORIGINS list, or the loopback default."""
    raw = os.environ.get("METTLE_CORS_ORIGINS", "").strip()
    if not raw:
        return list(DEFAULT_CORS_ORIGINS)
    return [o.strip() for o in raw.split(",") if o.strip()]


@lru_cache(maxsize=1)
def scan_roots() -> list[Path] | None:
    """Return resolved allow-list, or None when unset/empty.

    None means the path-jail is disabled (permissive mode with a startup warning).
    """
    raw = os.environ.get("METTLE_SCAN_ROOTS", "").strip()
    if not raw:
        return None
    parsed = [Path(p).expanduser().resolve() for p in raw.split(",") if p.strip()]
    return parsed if parsed else None


@lru_cache(maxsize=1)
def is_debug() -> bool:
    """METTLE_DEBUG in {1, true, yes} (case-insensitive) → True."""
    return os.environ.get("METTLE_DEBUG", "").strip().lower() in {"1", "true", "yes"}


def _cache_clear() -> None:
    """Test helper. Clears all lru_caches in this module."""
    token.cache_clear()
    cors_origins.cache_clear()
    scan_roots.cache_clear()
    is_debug.cache_clear()

"""SQLite-backed cache of resolved (manager, name, version) → SPDX results.

Effectively immutable mappings — once `react@18.2.0` is known to be MIT it
will always be MIT — so cache entries never expire on their own. Delete the
cache file to force re-fetch.

Stored at `$XDG_CACHE_HOME/mettle/license_cache.sqlite3` (with the same
fallback chain the file-metrics cache uses), or override via the
`METTLE_LICENSE_CACHE_PATH` env var.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
import threading
import time
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    manager TEXT NOT NULL,
    name TEXT NOT NULL,
    version TEXT,
    spdx TEXT,
    source TEXT NOT NULL,
    fetched_at INTEGER NOT NULL,
    PRIMARY KEY (manager, name, version)
);
"""


def _default_cache_path() -> Path:
    override = os.environ.get("METTLE_LICENSE_CACHE_PATH")
    if override:
        path = Path(override).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    cache_dir = Path(base) / "mettle"
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        cache_dir = Path(tempfile.gettempdir()) / "mettle"
        cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "license_cache.sqlite3"


class LicenseCache:
    """Process-wide cache. Concurrent-safe via an internal lock."""

    def __init__(self, path: Path | None = None, enabled: bool = True):
        self.path = path or _default_cache_path()
        self.enabled = enabled
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None

    def _connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.path, check_same_thread=False, timeout=5)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.executescript(_SCHEMA)
            self._conn.commit()
        return self._conn

    def get(self, manager: str, name: str, version: str | None) -> tuple[str | None, str] | None:
        """Return (spdx, source) on hit (spdx can be None — cached failure),
        or None when there's no entry at all (cache miss → fetch needed)."""
        if not self.enabled:
            return None
        with self._lock:
            conn = self._connection()
            row = conn.execute(
                "SELECT spdx, source FROM entries "
                "WHERE manager = ? AND name = ? AND version IS ?",
                (manager, name, version),
            ).fetchone()
        if row is None:
            return None
        return row[0], row[1]

    def put(
        self,
        manager: str,
        name: str,
        version: str | None,
        spdx: str | None,
        source: str,
    ) -> None:
        if not self.enabled:
            return
        with self._lock:
            conn = self._connection()
            conn.execute(
                """
                INSERT INTO entries(manager, name, version, spdx, source, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(manager, name, version) DO UPDATE SET
                    spdx = excluded.spdx,
                    source = excluded.source,
                    fetched_at = excluded.fetched_at
                """,
                (manager, name, version, spdx, source, int(time.time())),
            )
            conn.commit()

    def clear(self) -> None:
        with self._lock:
            conn = self._connection()
            conn.execute("DELETE FROM entries")
            conn.commit()

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

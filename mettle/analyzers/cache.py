"""SQLite-backed cache of per-file analysis results, keyed by (path, mtime, size).

Hot path: a directory scan that's already been analyzed once. Looking the file
up by absolute path + mtime + size is O(1) over an index, and skips reading the
file from disk plus running every regex over it.

If the file has changed (different mtime OR different size), the cache misses
and the analyzer runs normally; the new metrics are then written back.

Stored under `$XDG_CACHE_HOME/mettle/file_cache.sqlite3`, falling back to
`~/.cache/mettle/` and finally the system temp dir if neither is writable.
The cache is safe to delete at any time — it will rebuild itself.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import threading
from dataclasses import asdict
from pathlib import Path

from ..metrics.file_metrics import FileMetrics

_CACHE_SCHEMA_VERSION = 3

_CACHE_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS file_metrics (
    path TEXT PRIMARY KEY,
    mtime_ns INTEGER NOT NULL,
    size INTEGER NOT NULL,
    language TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    secrets_json TEXT NOT NULL DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_file_metrics_size ON file_metrics(size);
"""


def _default_cache_path() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    cache_dir = Path(base) / "mettle"
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        cache_dir = Path(tempfile.gettempdir()) / "mettle"
        cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "file_cache.sqlite3"


class FileMetricsCache:
    """Process-wide cache. Safe to call from many threads — uses a lock around
    the shared connection. The cache is opened lazily so importing this module
    doesn't touch the filesystem.
    """

    def __init__(self, path: Path | None = None, enabled: bool = True):
        self.path = path or _default_cache_path()
        self.enabled = enabled
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None
        self.hits = 0
        self.misses = 0

    # ------------------------------------------------------------------ admin

    def _connection(self) -> sqlite3.Connection:
        if self._conn is None:
            # `check_same_thread=False` because we serialise access via _lock.
            self._conn = sqlite3.connect(self.path, check_same_thread=False, timeout=5)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._conn.executescript(_CACHE_SCHEMA)
            self._enforce_schema_version(self._conn)
            self._conn.commit()
        return self._conn

    def _enforce_schema_version(self, conn: sqlite3.Connection) -> None:
        """If the on-disk schema version doesn't match the current one, drop
        and recreate the file_metrics table so the column layout is always
        current. (DELETE FROM only removes rows — it cannot add columns.)"""
        row = conn.execute("SELECT value FROM schema_meta WHERE key = 'version'").fetchone()
        on_disk = int(row[0]) if row else 0
        if on_disk != _CACHE_SCHEMA_VERSION:
            conn.execute("DROP TABLE IF EXISTS file_metrics")
            conn.executescript(_CACHE_SCHEMA)
            conn.execute(
                "INSERT OR REPLACE INTO schema_meta (key, value) VALUES ('version', ?)",
                (str(_CACHE_SCHEMA_VERSION),),
            )

    def reset_stats(self) -> None:
        self.hits = 0
        self.misses = 0

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    def clear(self) -> None:
        """Drop the whole cache (e.g. when changing analyzer logic)."""
        with self._lock:
            conn = self._connection()
            conn.execute("DELETE FROM file_metrics")
            conn.commit()

    # --------------------------------------------------------------- lookups

    def get(
        self, file_path: str, mtime_ns: int, size: int
    ) -> tuple[str, FileMetrics, list[dict]] | None:
        """Return `(language, metrics, secret_findings)` if there's a fresh cache hit, else None."""
        if not self.enabled:
            return None
        with self._lock:
            conn = self._connection()
            row = conn.execute(
                "SELECT mtime_ns, size, language, metrics_json, secrets_json "
                "FROM file_metrics WHERE path = ?",
                (file_path,),
            ).fetchone()
        if row is None:
            self.misses += 1
            return None
        cached_mtime, cached_size, language, payload, secrets_payload = row
        if cached_mtime != mtime_ns or cached_size != size:
            # Stale; remove so a later put() can overwrite cleanly.
            self.misses += 1
            return None
        try:
            metrics = FileMetrics(**json.loads(payload))
            findings = json.loads(secrets_payload) if secrets_payload else []
        except (TypeError, ValueError, json.JSONDecodeError):
            self.misses += 1
            return None
        self.hits += 1
        return language, metrics, findings

    def put(
        self,
        file_path: str,
        mtime_ns: int,
        size: int,
        language: str,
        metrics: FileMetrics,
        secret_findings: list[dict] | None = None,
    ) -> None:
        if not self.enabled:
            return
        payload = json.dumps(asdict(metrics))
        secrets_json = json.dumps(secret_findings or [])
        with self._lock:
            conn = self._connection()
            conn.execute(
                """
                INSERT INTO file_metrics(path, mtime_ns, size, language, metrics_json, secrets_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    mtime_ns = excluded.mtime_ns,
                    size = excluded.size,
                    language = excluded.language,
                    metrics_json = excluded.metrics_json,
                    secrets_json = excluded.secrets_json
                """,
                (file_path, mtime_ns, size, language, payload, secrets_json),
            )
            conn.commit()


# Module-level singleton for convenient sharing across analyzer instances.
_default_cache: FileMetricsCache | None = None
_default_cache_lock = threading.Lock()


def get_default_cache() -> FileMetricsCache:
    global _default_cache
    if _default_cache is None:
        with _default_cache_lock:
            if _default_cache is None:
                disabled = os.environ.get("METTLE_DISABLE_CACHE") == "1"
                _default_cache = FileMetricsCache(enabled=not disabled)
    return _default_cache

"""Tests for FileMetricsCache 3-tuple get/put with secret findings."""

import pytest

from mettle.analyzers.cache import FileMetricsCache
from mettle.metrics.file_metrics import FileMetrics


@pytest.fixture
def cache(tmp_path):
    return FileMetricsCache(path=tmp_path / "test_cache.sqlite3")


def _store(cache, path, mtime, size, language, metrics, findings):
    """Adapter that calls the existing setter regardless of its name."""
    for name in ("put", "store", "set", "save", "add"):
        fn = getattr(cache, name, None)
        if fn is not None:
            try:
                return fn(path, mtime, size, language, metrics, secret_findings=findings)
            except TypeError:
                raise
    raise AttributeError("No known setter method on FileMetricsCache")


def test_store_and_get_with_empty_findings(cache, tmp_path):
    f = tmp_path / "src.py"
    f.write_text("print('hi')")
    metrics = FileMetrics(total_lines=1, code_lines=1)

    _store(cache, str(f), 12345, 11, "python", metrics, [])

    hit = cache.get(str(f), 12345, 11)
    assert hit is not None
    language, returned_metrics, findings = hit
    assert language == "python"
    assert returned_metrics.code_lines == 1
    assert findings == []


def test_store_and_get_with_findings(cache, tmp_path):
    f = tmp_path / "src.py"
    f.write_text("print('hi')")
    metrics = FileMetrics(total_lines=1, code_lines=1)

    finding = {
        "file": "src.py",
        "line": 1,
        "kind": "aws_access_key_id",
        "snippet_hash": "abcdef0123456789",
        "severity": "high",
    }
    _store(cache, str(f), 99, 50, "python", metrics, [finding])

    hit = cache.get(str(f), 99, 50)
    assert hit is not None
    _, _, findings = hit
    assert findings == [finding]


def test_cache_miss_when_mtime_changes(cache, tmp_path):
    f = tmp_path / "src.py"
    f.write_text("x")
    metrics = FileMetrics(total_lines=1)
    _store(cache, str(f), 100, 1, "python", metrics, [])
    # Different mtime → miss
    assert cache.get(str(f), 101, 1) is None

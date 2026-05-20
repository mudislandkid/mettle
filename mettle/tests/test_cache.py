"""Tests for the SQLite-backed FileMetrics cache."""

import os
import tempfile
import unittest
from pathlib import Path

from ..analyzers.cache import FileMetricsCache
from ..metrics.file_metrics import FileMetrics


class TestFileMetricsCache(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.cache_path = Path(self.tmpdir.name) / "cache.sqlite3"
        self.cache = FileMetricsCache(path=self.cache_path)

    def tearDown(self):
        self.cache.close()
        self.tmpdir.cleanup()

    def _metrics(self, total: int = 100) -> FileMetrics:
        m = FileMetrics()
        m.total_lines = total
        m.code_lines = total - 5
        m.comment_lines = 3
        m.blank_lines = 2
        m.functions = 4
        return m

    def test_put_then_get_returns_same_metrics(self):
        m = self._metrics(123)
        self.cache.put("/some/file.py", mtime_ns=42, size=1024, language="Python", metrics=m)
        hit = self.cache.get("/some/file.py", mtime_ns=42, size=1024)
        self.assertIsNotNone(hit)
        lang, returned = hit
        self.assertEqual(lang, "Python")
        self.assertEqual(returned.total_lines, 123)
        self.assertEqual(returned.code_lines, 118)
        self.assertEqual(self.cache.hits, 1)
        self.assertEqual(self.cache.misses, 0)

    def test_miss_on_mtime_change(self):
        self.cache.put("/x.py", 100, 50, "Python", self._metrics())
        self.assertIsNone(self.cache.get("/x.py", mtime_ns=101, size=50))
        self.assertEqual(self.cache.misses, 1)

    def test_miss_on_size_change(self):
        self.cache.put("/x.py", 100, 50, "Python", self._metrics())
        self.assertIsNone(self.cache.get("/x.py", mtime_ns=100, size=51))
        self.assertEqual(self.cache.misses, 1)

    def test_overwrite_keeps_one_row(self):
        self.cache.put("/x.py", 1, 10, "Python", self._metrics(10))
        self.cache.put("/x.py", 2, 20, "Python", self._metrics(20))
        hit = self.cache.get("/x.py", mtime_ns=2, size=20)
        self.assertIsNotNone(hit)
        self.assertEqual(hit[1].total_lines, 20)
        # Old key should miss now.
        self.assertIsNone(self.cache.get("/x.py", mtime_ns=1, size=10))

    def test_disabled_cache_does_nothing(self):
        disabled = FileMetricsCache(path=self.cache_path, enabled=False)
        disabled.put("/y.py", 1, 1, "Python", self._metrics())
        self.assertIsNone(disabled.get("/y.py", mtime_ns=1, size=1))
        self.assertEqual(disabled.hits, 0)
        self.assertEqual(disabled.misses, 0)

    def test_clear_empties_cache(self):
        self.cache.put("/a.py", 1, 1, "Python", self._metrics())
        self.cache.put("/b.py", 2, 2, "Python", self._metrics())
        self.cache.clear()
        self.assertIsNone(self.cache.get("/a.py", mtime_ns=1, size=1))
        self.assertIsNone(self.cache.get("/b.py", mtime_ns=2, size=2))


class TestFileAnalyzerCacheIntegration(unittest.TestCase):
    """Confirm the FileAnalyzer actually consults the cache on the hot path.

    Skipped automatically if `rich` (a FileAnalyzer dep) is not importable —
    keeps the test suite green in minimal CI environments.
    """

    def setUp(self):
        try:
            from ..analyzers.file_analyzer import FileAnalyzer  # noqa: F401
        except ModuleNotFoundError:
            self.skipTest("FileAnalyzer dependencies not installed")
        self.tmpdir = tempfile.TemporaryDirectory()
        self.cache_path = Path(self.tmpdir.name) / "cache.sqlite3"
        self.cache = FileMetricsCache(path=self.cache_path)

    def tearDown(self):
        self.cache.close()
        self.tmpdir.cleanup()

    def test_second_analyze_is_a_cache_hit(self):
        from ..analyzers.file_analyzer import FileAnalyzer

        src = Path(self.tmpdir.name) / "demo.py"
        src.write_text("def foo():\n    return 1\n")
        analyzer = FileAnalyzer(cache=self.cache)
        lang1, m1 = analyzer.analyze_file(str(src))
        lang2, m2 = analyzer.analyze_file(str(src))
        self.assertEqual(lang1, "Python")
        self.assertEqual(lang2, "Python")
        self.assertEqual(m1.total_lines, m2.total_lines)
        self.assertEqual(self.cache.hits, 1, "second call must hit cache")
        self.assertEqual(self.cache.misses, 1, "first call must miss cache")

    def test_modified_file_misses(self):
        from ..analyzers.file_analyzer import FileAnalyzer

        src = Path(self.tmpdir.name) / "demo.py"
        src.write_text("def foo():\n    return 1\n")
        analyzer = FileAnalyzer(cache=self.cache)
        analyzer.analyze_file(str(src))
        # Make the size & mtime change so the cache key is fresh.
        src.write_text("def foo():\n    return 2\n# changed\n")
        os.utime(src, ns=(0, 9_999_999_999))  # bump mtime explicitly
        analyzer.analyze_file(str(src))
        self.assertGreaterEqual(self.cache.misses, 2)
        self.assertEqual(self.cache.hits, 0)


if __name__ == "__main__":
    unittest.main()

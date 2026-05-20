"""Tests for third-party analyzer discovery via importlib.metadata entry points."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from mettle.analyzers import factory as factory_mod
from mettle.analyzers.base import BaseAnalyzer


class CobolAnalyzer(BaseAnalyzer):
    LANGUAGE = "COBOL"
    EXTENSIONS = [".cob", ".cbl"]

    def analyze(self, content, file_size=0, line_count=0, byte_count=0):
        # The factory only ever calls .analyze() in real code paths; these
        # tests don't analyse any files, but we still need a no-op impl
        # so the class is concrete.
        from mettle.metrics.file_metrics import FileMetrics

        return FileMetrics()


class NoExtensionsAnalyzer(BaseAnalyzer):
    LANGUAGE = "Noop"
    EXTENSIONS = []

    def analyze(self, content, file_size=0, line_count=0, byte_count=0):
        from mettle.metrics.file_metrics import FileMetrics

        return FileMetrics()


class NotAnAnalyzer:
    """Deliberately not a BaseAnalyzer subclass — should be rejected."""

    LANGUAGE = "Bogus"
    EXTENSIONS = [".bogus"]


def _fake_ep(name: str, loader):
    """Build a fake EntryPoint-like object the factory can call .load() on."""
    return SimpleNamespace(name=name, load=loader)


class TestEntryPointPlugins(unittest.TestCase):
    def _patch_eps(self, eps_list):
        """Patch importlib.metadata.entry_points to return our list."""

        def fake_entry_points(group=None, **_kwargs):
            if group == factory_mod.ENTRY_POINT_GROUP:
                return eps_list
            return []

        return patch("importlib.metadata.entry_points", fake_entry_points)

    def test_registers_valid_plugin_with_extensions(self):
        ep = _fake_ep("cobol", lambda: CobolAnalyzer)
        with self._patch_eps([ep]):
            factory = factory_mod.AnalyzerFactory()

        self.assertIn("COBOL", factory.analyzers)
        self.assertIs(factory.analyzers["COBOL"], CobolAnalyzer)
        self.assertEqual(factory.file_extensions["COBOL"], {".cob", ".cbl"})
        self.assertEqual(factory.get_language("payroll.cob"), "COBOL")
        # Instance cache should produce the new analyzer class.
        self.assertIsInstance(factory.get_analyzer("payroll.cob"), CobolAnalyzer)

    def test_normalises_extensions_without_dot(self):
        class BareExtAnalyzer(BaseAnalyzer):
            LANGUAGE = "Bare"
            EXTENSIONS = ["bare", ".already", "  DOT  "]

            def analyze(self, content, file_size=0, line_count=0, byte_count=0):
                from mettle.metrics.file_metrics import FileMetrics

                return FileMetrics()

        ep = _fake_ep("bare", lambda: BareExtAnalyzer)
        with self._patch_eps([ep]):
            factory = factory_mod.AnalyzerFactory()

        # All three should be normalised to lowercase, dot-prefixed.
        self.assertEqual(factory.file_extensions["Bare"], {".bare", ".already", ".dot"})

    def test_plugin_overrides_builtin_language(self):
        """If a plugin claims an existing language, it must take precedence."""

        class StricterPython(BaseAnalyzer):
            LANGUAGE = "Python"
            EXTENSIONS = [".py"]

            def analyze(self, content, file_size=0, line_count=0, byte_count=0):
                from mettle.metrics.file_metrics import FileMetrics

                return FileMetrics()

        ep = _fake_ep("python-strict", lambda: StricterPython)
        with self._patch_eps([ep]):
            factory = factory_mod.AnalyzerFactory()

        self.assertIs(factory.analyzers["Python"], StricterPython)
        # The instance cache must be invalidated so subsequent get_analyzer
        # calls don't return a stale PythonAstAnalyzer.
        self.assertIsInstance(factory.get_analyzer("foo.py"), StricterPython)

    def test_skips_plugin_that_raises_on_load(self):
        def boom():
            raise ImportError("simulated broken plugin")

        good_ep = _fake_ep("cobol", lambda: CobolAnalyzer)
        bad_ep = _fake_ep("broken", boom)
        with self._patch_eps([bad_ep, good_ep]):
            factory = factory_mod.AnalyzerFactory()

        # Good plugin still loaded; bad one was logged-and-skipped.
        self.assertIn("COBOL", factory.analyzers)

    def test_skips_non_analyzer_subclass(self):
        ep = _fake_ep("bogus", lambda: NotAnAnalyzer)
        with self._patch_eps([ep]):
            factory = factory_mod.AnalyzerFactory()
        self.assertNotIn("Bogus", factory.analyzers)

    def test_skips_plugin_without_extensions(self):
        ep = _fake_ep("noop", lambda: NoExtensionsAnalyzer)
        with self._patch_eps([ep]):
            factory = factory_mod.AnalyzerFactory()
        self.assertNotIn("Noop", factory.analyzers)

    def test_entry_point_languages_excluded_from_cache(self):
        """Plugins are re-resolved each run, so we must not pin them in the cache file."""
        ep = _fake_ep("cobol", lambda: CobolAnalyzer)
        with self._patch_eps([ep]):
            factory = factory_mod.AnalyzerFactory()

        # After construction, the cache write should have excluded COBOL.
        # We re-call _save_registrations and inspect cache_data via the file.
        import json

        if factory._cache_file.exists():
            cached = json.loads(factory._cache_file.read_text())
            self.assertNotIn("COBOL", cached)

        self.assertIn("COBOL", factory._entry_point_languages)


if __name__ == "__main__":
    unittest.main()

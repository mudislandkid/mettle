"""Tests for watch-mode helpers (pure functions; the filesystem watcher itself isn't exercised)."""

import io
import unittest
from unittest.mock import MagicMock

from rich.console import Console

from code_counter.metrics.file_metrics import FileMetrics
from code_counter import watch as watch_mod


def _make_metrics(total_files: int, **field_overrides) -> dict:
    """Build the dict shape DirectoryAnalyzer.analyze_directory returns."""
    fm = FileMetrics(
        total_lines=field_overrides.get('total_lines', 0),
        code_lines=field_overrides.get('code_lines', 0),
        comment_lines=field_overrides.get('comment_lines', 0),
        blank_lines=field_overrides.get('blank_lines', 0),
    )
    # Pile remaining fields directly onto the FileMetrics instance.
    for field in ('functions', 'classes', 'todos', 'imports'):
        setattr(fm, field, field_overrides.get(field, 0))
    return {
        'total_files': total_files,
        'metrics_by_language': {'Python': fm},
    }


class TestWatchAggregate(unittest.TestCase):
    def test_aggregate_sums_per_language_fields(self):
        metrics = _make_metrics(
            total_files=5, total_lines=100, code_lines=80,
            comment_lines=10, blank_lines=10,
            functions=4, classes=2, todos=3, imports=7,
        )
        totals = watch_mod._aggregate_totals(metrics)
        self.assertEqual(totals['total_files'], 5)
        self.assertEqual(totals['total_lines'], 100)
        self.assertEqual(totals['code_lines'], 80)
        self.assertEqual(totals['functions'], 4)
        self.assertEqual(totals['todos'], 3)

    def test_aggregate_handles_empty_metrics(self):
        totals = watch_mod._aggregate_totals({'total_files': 0, 'metrics_by_language': {}})
        for field in watch_mod._TRACKED_FIELDS:
            self.assertEqual(totals[field], 0)


class TestWatchDelta(unittest.TestCase):
    def _capture(self, before, after) -> str:
        buf = io.StringIO()
        console = Console(file=buf, force_terminal=False, color_system=None, width=120)
        watch_mod._print_delta(console, before, after)
        return buf.getvalue()

    def test_delta_silent_when_nothing_changes(self):
        out = self._capture({'total_lines': 100}, {'total_lines': 100})
        self.assertIn("no metric changes", out)

    def test_delta_reports_per_field_movement(self):
        before = {'total_lines': 100, 'code_lines': 80, 'todos': 3}
        after = {'total_lines': 120, 'code_lines': 90, 'todos': 5}
        out = self._capture(before, after)
        self.assertIn('total_lines', out)
        self.assertIn('+20', out)
        self.assertIn('code_lines', out)
        self.assertIn('+10', out)
        # TODOs went up — that's bad, the delta still appears.
        self.assertIn('todos', out)
        self.assertIn('+2', out)

    def test_delta_handles_negative_movement(self):
        before = {'total_lines': 120, 'todos': 5}
        after = {'total_lines': 100, 'todos': 3}
        out = self._capture(before, after)
        # No "+" prefix when delta is negative.
        self.assertIn('-20', out)
        self.assertIn('-2', out)


class TestWatchEntry(unittest.TestCase):
    """Quick sanity checks on the entry point without spinning up a real watcher."""

    def test_missing_directory_returns_2(self):
        args = MagicMock(
            check=False, watch=True, directory=None,
            debug=False, max_lines=0, exclude_types=None,
            exclude_dirs=None, watch_debounce=1500,
        )
        rc = watch_mod.run_watch(args, Console(file=io.StringIO(), force_terminal=False))
        self.assertEqual(rc, 2)

    def test_non_directory_returns_2(self):
        args = MagicMock(
            check=False, watch=True, directory='/definitely/not/a/path/9c8b3',
            debug=False, max_lines=0, exclude_types=None,
            exclude_dirs=None, watch_debounce=1500,
        )
        rc = watch_mod.run_watch(args, Console(file=io.StringIO(), force_terminal=False))
        # If watchfiles isn't installed we get rc=2 from the early import-error
        # branch — same exit code, same outcome from the user's perspective.
        self.assertEqual(rc, 2)


if __name__ == '__main__':
    unittest.main()

"""Tests for the --fail-on parser used by `mettle --check`."""

import unittest


class TestParseFailOn(unittest.TestCase):
    def setUp(self):
        try:
            from ..__main__ import _parse_fail_on
        except ModuleNotFoundError:
            self.skipTest("__main__ deps not installed")
        self._parse = _parse_fail_on

    def test_parses_known_keys(self):
        thresholds = self._parse(
            [
                "file-lines-over=500",
                "functions-over=50",
                "cyclomatic-over=20",
                "todo-density-over=10",
            ]
        )
        self.assertEqual(thresholds["file-lines-over"], 500)
        self.assertEqual(thresholds["functions-over"], 50)
        self.assertEqual(thresholds["cyclomatic-over"], 20)
        self.assertEqual(thresholds["todo-density-over"], 10)

    def test_missing_equals_raises(self):
        with self.assertRaises(ValueError):
            self._parse(["file-lines-over 500"])

    def test_unknown_key_raises(self):
        with self.assertRaises(ValueError):
            self._parse(["blah=1"])

    def test_non_integer_raises(self):
        with self.assertRaises(ValueError):
            self._parse(["file-lines-over=ten"])

    def test_empty_list_returns_empty_dict(self):
        self.assertEqual(self._parse([]), {})


if __name__ == "__main__":
    unittest.main()

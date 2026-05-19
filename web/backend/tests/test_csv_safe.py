"""Tests for the CSV formula-injection guard used in routes_export."""

import unittest

from web.backend.api.routes_export import _safe_cell


class TestSafeCell(unittest.TestCase):
    def test_leading_equals_gets_apostrophe(self):
        self.assertEqual(_safe_cell("=SUM(A1:A9)"), "'=SUM(A1:A9)")

    def test_leading_plus_minus_at(self):
        self.assertEqual(_safe_cell("+1"), "'+1")
        self.assertEqual(_safe_cell("-2"), "'-2")
        self.assertEqual(_safe_cell("@foo"), "'@foo")

    def test_tab_or_cr_prefix(self):
        self.assertEqual(_safe_cell("\t=BAD"), "'\t=BAD")
        self.assertEqual(_safe_cell("\rfoo"), "'\rfoo")

    def test_plain_text_unchanged(self):
        self.assertEqual(_safe_cell("Greg's project"), "Greg's project")
        self.assertEqual(_safe_cell(""), "")
        self.assertEqual(_safe_cell(None), "")
        self.assertEqual(_safe_cell(42), "42")


if __name__ == "__main__":
    unittest.main()

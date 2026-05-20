"""
Tests for the reporter classes.

This module contains unit tests for the various reporter classes
that generate output from the code analysis results.
"""

import os
import tempfile
import unittest

from mettle.metrics.file_metrics import FileMetrics
from mettle.reporters.console import ConsoleReporter
from mettle.reporters.markdown import MarkdownReporter

try:
    from mettle.reporters.html import HTMLReporter

    _HTML_AVAILABLE = True
except ImportError:
    _HTML_AVAILABLE = False


class TestReporters(unittest.TestCase):
    """Test cases for the reporter classes."""

    def setUp(self):
        """Set up test fixtures."""
        # Create sample metrics for testing
        self.metrics_by_language = {
            "Python": FileMetrics(total_lines=100, code_lines=80, comment_lines=10, blank_lines=10)
        }
        self.language_stats = {
            "Python": {"total_files": 5, "avg_lines_per_file": 20.0, "median_lines_per_file": 18.0}
        }
        self.largest_line_files = {"Python": ("test.py", 100)}

    def test_console_reporter_initialization(self):
        """Test that ConsoleReporter initializes correctly."""
        reporter = ConsoleReporter(
            metrics_by_language=self.metrics_by_language,
            language_stats=self.language_stats,
            total_files=5,
            total_dirs=2,
            largest_line_files=self.largest_line_files,
        )
        self.assertEqual(reporter.total_lines, 100)
        self.assertEqual(reporter.total_code_lines, 80)
        self.assertEqual(reporter.total_comment_lines, 10)
        self.assertEqual(reporter.total_blank_lines, 10)

    def test_markdown_reporter_initialization(self):
        """Test that MarkdownReporter initializes correctly."""
        reporter = MarkdownReporter(
            metrics_by_language=self.metrics_by_language,
            language_stats=self.language_stats,
            total_files=5,
            total_dirs=2,
            largest_line_files=self.largest_line_files,
            project_name="Test Project",
        )
        self.assertEqual(reporter.project_name, "Test Project")
        self.assertEqual(reporter.total_lines, 100)
        self.assertEqual(reporter.total_code_lines, 80)

    def test_markdown_report_generation(self):
        """Test that MarkdownReporter generates a report file."""
        reporter = MarkdownReporter(
            metrics_by_language=self.metrics_by_language,
            language_stats=self.language_stats,
            total_files=5,
            total_dirs=2,
            largest_line_files=self.largest_line_files,
            project_name="Test Project",
        )

        # Create a temporary file for the report
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as temp:
            temp_path = temp.name

        try:
            # Generate the report
            reporter.generate_report(temp_path)

            # Check that the file exists and has content
            self.assertTrue(os.path.exists(temp_path))
            with open(temp_path) as f:
                content = f.read()
                self.assertIn("# Test Project", content)
                self.assertIn("## Code Analysis Report", content)
                self.assertIn("| Total Lines | 100 |", content)
                self.assertIn("| Code Lines | 80 |", content)
                self.assertIn("| Largest File | test.py |", content)
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @unittest.skipUnless(_HTML_AVAILABLE, "matplotlib not installed; HTMLReporter unavailable")
    def test_html_report_generation(self):
        """HTMLReporter writes a self-contained .html file with inline SVG and key metrics."""
        reporter = HTMLReporter(
            metrics_by_language=self.metrics_by_language,
            language_stats=self.language_stats,
            total_files=5,
            total_dirs=2,
            largest_line_files=self.largest_line_files,
            project_name="Test Project",
        )

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as temp:
            temp_path = temp.name

        try:
            reporter.generate_report(temp_path)
            self.assertTrue(os.path.exists(temp_path))
            with open(temp_path, encoding="utf-8") as f:
                content = f.read()

            self.assertIn("<!DOCTYPE html>", content)
            self.assertIn("Test Project", content)
            self.assertIn("Summary statistics", content)
            # Numbers are formatted with commas; raw 100/80 still appear in the SVG / table.
            self.assertIn("100", content)
            self.assertIn("80", content)
            # Charts must be embedded inline as SVG (no external script/img tags).
            self.assertIn("<svg", content)
            self.assertNotIn("<script", content)
            # No external stylesheet/script references (xmlns="http://..." namespace URIs
            # in the SVG are fine, but `<link href=`/`<script src=` are not).
            self.assertNotIn("<link ", content)
            self.assertNotIn('src="http', content)
            self.assertNotIn("src='http", content)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @unittest.skipUnless(_HTML_AVAILABLE, "matplotlib not installed; HTMLReporter unavailable")
    def test_html_escapes_project_name(self):
        """Project name with HTML-special chars is escaped, not interpreted as markup."""
        reporter = HTMLReporter(
            metrics_by_language=self.metrics_by_language,
            language_stats=self.language_stats,
            total_files=5,
            total_dirs=2,
            largest_line_files=self.largest_line_files,
            project_name="<script>alert(1)</script>",
        )

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as temp:
            temp_path = temp.name
        try:
            reporter.generate_report(temp_path)
            with open(temp_path, encoding="utf-8") as f:
                content = f.read()
            self.assertIn("&lt;script&gt;", content)
            # The literal injected tag must not survive escaping.
            self.assertNotIn("<script>alert(1)</script>", content)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


if __name__ == "__main__":
    unittest.main()

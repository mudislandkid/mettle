"""Smoke tests for the Click CLI surface."""

import subprocess
import sys


def test_cli_help_exits_zero():
    """`mettle --help` should exit zero and list the subcommands."""
    result = subprocess.run(
        [sys.executable, "-m", "mettle", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"exit {result.returncode}, stderr: {result.stderr}"
    for sub in ("scan", "batch", "watch", "check", "web"):
        assert sub in result.stdout, f"subcommand {sub!r} missing from --help"


def test_cli_version_flag():
    """`mettle --version` should print the package version."""
    result = subprocess.run(
        [sys.executable, "-m", "mettle", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "0.9.0" in result.stdout


def test_cli_scan_help_lists_known_flags():
    """`mettle scan --help` should show the inherited flags."""
    result = subprocess.run(
        [sys.executable, "-m", "mettle", "scan", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    for flag in ("--no-pdf", "--no-html", "--debug", "--compare-to-last"):
        assert flag in result.stdout, f"flag {flag!r} missing"


def test_cli_digest_help_lists_flags():
    """`mettle digest --help` should show the subcommand flags."""
    result = subprocess.run(
        [sys.executable, "-m", "mettle", "digest", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    for flag in ("--since", "--top", "--stale-days", "--format", "--out"):
        assert flag in result.stdout, f"flag {flag!r} missing"

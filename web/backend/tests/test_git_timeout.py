"""Tests for git_safe.run_git — hardened env + 30s wall-clock timeout."""

import subprocess
from unittest.mock import patch

import pytest

from web.backend.services.git_safe import (
    GIT_TIMEOUT_SECONDS,
    GitTimeoutError,
    run_git,
)


def test_run_git_returns_completed_process_on_success(tmp_path):
    """Real git call (the cwd doesn't need to be a repo for `git --version`).
    Skipped if no git on PATH.
    """
    if subprocess.run(["which", "git"], capture_output=True).returncode != 0:
        pytest.skip("git not on PATH")
    result = run_git(["--version"], cwd=tmp_path)
    assert result.returncode == 0
    assert "git version" in result.stdout


def test_run_git_raises_git_timeout_error_on_timeout(tmp_path):
    """Patch subprocess.run to raise TimeoutExpired and confirm the wrapper translates it."""
    fake_exc = subprocess.TimeoutExpired(cmd="git", timeout=GIT_TIMEOUT_SECONDS)
    with patch("subprocess.run", side_effect=fake_exc):
        with pytest.raises(GitTimeoutError) as exc:
            run_git(["log"], cwd=tmp_path)
    assert "timed out" in str(exc.value)
    assert str(GIT_TIMEOUT_SECONDS) in str(exc.value)


def test_run_git_passes_hardened_env(tmp_path):
    """Confirm the hardened env is in effect (no system/global config, no terminal prompt)."""
    captured = {}

    def fake_run(*args, **kwargs):
        captured["env"] = kwargs["env"]
        captured["args"] = args[0]
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")

    with patch("subprocess.run", side_effect=fake_run):
        run_git(["status"], cwd=tmp_path)

    env = captured["env"]
    assert env["GIT_CONFIG_NOSYSTEM"] == "1"
    assert env["GIT_CONFIG_GLOBAL"] == "/dev/null"
    assert env["GIT_TERMINAL_PROMPT"] == "0"
    assert env["GIT_OPTIONAL_LOCKS"] == "0"
    # PATH is intentionally preserved so git itself resolves.
    assert "PATH" in env
    # --no-pager is always prepended.
    assert captured["args"][:2] == ["git", "--no-pager"]

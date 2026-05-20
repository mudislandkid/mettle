"""Hardened git subprocess helper.

A single `run_git()` call site owns:
- the locked-down env (no system/global config, no terminal prompts, no optional locks)
- the 30s wall-clock timeout (raises GitTimeoutError, not None)
- the --no-pager prefix that prevents git from invoking less/more

Callers that need to distinguish hang-vs-fail should catch GitTimeoutError
separately from inspecting CompletedProcess.returncode.
"""

import os
import subprocess
from pathlib import Path

GIT_TIMEOUT_SECONDS = 30

_HARDENED_ENV = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "HOME": "/dev/null",
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_OPTIONAL_LOCKS": "0",
    # PATH must be present so the `git` executable itself resolves.
    "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/local/bin"),
}


class GitTimeoutError(Exception):
    """A git subprocess exceeded GIT_TIMEOUT_SECONDS."""


def run_git(args: list[str], cwd: Path | str) -> subprocess.CompletedProcess:
    """Run a hardened git command with a wall-clock timeout.

    Always prepends `--no-pager`. Returns the CompletedProcess on completion
    (success OR non-zero exit). Raises GitTimeoutError if the subprocess
    didn't terminate within GIT_TIMEOUT_SECONDS.
    """
    try:
        return subprocess.run(
            ["git", "--no-pager", *args],
            cwd=str(cwd),
            env=_HARDENED_ENV,
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise GitTimeoutError(
            f"git {args[0] if args else ''} timed out after " f"{GIT_TIMEOUT_SECONDS}s in {cwd}"
        ) from e

"""Analyzer service wrapping existing Mettle modules."""

import sys
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

# Add parent directories to path to import existing modules
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from batch_analyze import (
    analyze_project,
    is_known_public_sdk,
    is_owned_by_user,
    is_project_directory,
)
from mettle.analyzers.code_analyzer import CodeAnalyzer

WRAPPER_REPO_MIN_CHILDREN = 3
CATEGORY_MIN_CHILDREN = 2

# Folder names commonly used as containers for sub-projects in monorepos.
# When we see one of these AND it houses multiple project-shaped children,
# we expand into those children instead of treating the container as one
# project (or skipping it because the name is in INTERNAL_FOLDER_NAMES).
_CATEGORY_FOLDERS = frozenset(
    {
        "apps",
        "packages",
        "services",
        "libs",
        "libraries",
        "modules",
        "crates",
        "tools",
        "projects",
    }
)


def _wrapper_repo_children(path: Path, include_internal: bool) -> list[Path] | None:
    """Return git-repo children if `path` is a wrapper-repo, else None.

    A directory is treated as a wrapper if at least WRAPPER_REPO_MIN_CHILDREN
    of its direct children are themselves git repositories. This handles
    monorepos-of-repos (clone-all.sh style layouts) where the wrapper repo
    isn't the right unit of analysis on its own.
    """
    try:
        children = [c for c in path.iterdir() if c.is_dir()]
    except (OSError, PermissionError):
        return None

    repo_children = [
        c for c in children if (c / ".git").exists() and is_project_directory(c, include_internal)
    ]
    if len(repo_children) >= WRAPPER_REPO_MIN_CHILDREN:
        return repo_children
    return None


def _category_dir_children(path: Path) -> list[Path] | None:
    """If `path` looks like a monorepo "category folder" (apps/, packages/,
    services/ etc.) housing multiple sub-projects, return them. Else None.

    Children are checked with ``include_internal=True`` deliberately — once
    we've decided to recurse into e.g. `apps/`, names like `apps/api` or
    `apps/web` are obviously projects, not folders we want to filter out
    just because they appear in INTERNAL_FOLDER_NAMES.
    """
    if path.name.lower() not in _CATEGORY_FOLDERS:
        return None
    try:
        children = sorted(c for c in path.iterdir() if c.is_dir())
    except (OSError, PermissionError):
        return None
    project_children = [c for c in children if is_project_directory(c, include_internal=True)]
    if len(project_children) >= CATEGORY_MIN_CHILDREN:
        return project_children
    return None


class AnalyzerService:
    """Service for analyzing project directories."""

    def __init__(self):
        self.analyzer = CodeAnalyzer(debug=False)

    def discover_projects(
        self,
        directory: str,
        github_user: str | None = None,
        skip_public_sdks: bool = False,
        include_internal: bool = False,
    ) -> list[Path]:
        """Discover project directories with filtering.

        Two automatic expansions kick in for monorepo layouts:

        - **Wrapper-repo expansion**: a candidate dir containing 3+ child git
          repos (gentlewatch-style clone-all monorepos) is replaced by its
          children.
        - **Category-folder expansion**: a dir named `apps/`, `packages/`,
          `services/`, `libs/`, `crates/`, etc. that houses 2+ project-shaped
          children is replaced by those children. Applies whether the
          container dir itself passes the normal project filter or was being
          dropped by the INTERNAL_FOLDER_NAMES rule.
        """
        parent_dir = Path(directory).resolve()

        if not parent_dir.exists():
            raise ValueError(f"Directory not found: {parent_dir}")

        if not parent_dir.is_dir():
            raise ValueError(f"Not a directory: {parent_dir}")

        subdirs = [d for d in parent_dir.iterdir() if d.is_dir()]

        expanded: list[Path] = []
        for d in subdirs:
            passes = is_project_directory(d, include_internal)
            # Wrapper-repo: replaces d entirely with its child repos.
            if passes:
                wrapper_children = _wrapper_repo_children(d, include_internal)
                if wrapper_children:
                    expanded.extend(wrapper_children)
                    continue
            # Category-folder expansion. Applies whether d passes the normal
            # filter or not — `apps/` itself rarely has a manifest, but its
            # children almost always do.
            category_children = _category_dir_children(d)
            if passes:
                expanded.append(d)
            if category_children:
                expanded.extend(category_children)

        # Dedup while preserving order in case the same path was added twice
        # (e.g. d itself + via category expansion of a sibling pointing to it).
        seen: set[Path] = set()
        project_dirs: list[Path] = []
        for d in expanded:
            key = d.resolve()
            if key in seen:
                continue
            seen.add(key)
            project_dirs.append(d)

        if skip_public_sdks:
            project_dirs = [d for d in project_dirs if not is_known_public_sdk(d)]

        if github_user:
            project_dirs = [d for d in project_dirs if is_owned_by_user(d, github_user)]

        return sorted(project_dirs)

    def analyze_projects(
        self,
        project_dirs: list[Path],
        max_files: int = 0,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> list[dict]:
        """Analyze list of projects, returning serializable results."""
        results = []
        total = len(project_dirs)

        for i, project_dir in enumerate(project_dirs, 1):
            if progress_callback:
                progress_callback(i, total, project_dir.name)

            summary = analyze_project(project_dir, self.analyzer)

            if summary and summary.total_files > 0:
                # Skip projects exceeding max_files threshold
                if max_files > 0 and summary.total_files > max_files:
                    continue

                # Convert to dict and add path
                result = asdict(summary)
                result["path"] = str(project_dir)
                results.append(result)

        return results

    def analyze_directory(
        self,
        directory: str,
        github_user: str | None = None,
        skip_public_sdks: bool = False,
        include_internal: bool = False,
        max_files: int = 0,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> list[dict]:
        """Full analysis pipeline: discover and analyze projects."""
        project_dirs = self.discover_projects(
            directory,
            github_user=github_user,
            skip_public_sdks=skip_public_sdks,
            include_internal=include_internal,
        )

        return self.analyze_projects(
            project_dirs,
            max_files=max_files,
            progress_callback=progress_callback,
        )


def validate_directory(path: str) -> dict:
    """Validate a directory path exists and is accessible."""
    p = Path(path)
    return {
        "exists": p.exists(),
        "is_directory": p.is_dir() if p.exists() else False,
        "path": str(p.resolve()) if p.exists() else path,
    }

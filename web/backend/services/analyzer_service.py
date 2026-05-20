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
        """Discover project directories with filtering."""
        parent_dir = Path(directory).resolve()

        if not parent_dir.exists():
            raise ValueError(f"Directory not found: {parent_dir}")

        if not parent_dir.is_dir():
            raise ValueError(f"Not a directory: {parent_dir}")

        # Get direct subdirectories
        subdirs = [d for d in parent_dir.iterdir() if d.is_dir()]

        # Filter to project directories
        project_dirs = [d for d in subdirs if is_project_directory(d, include_internal)]

        # Filter out known public SDKs
        if skip_public_sdks:
            project_dirs = [d for d in project_dirs if not is_known_public_sdk(d)]

        # Filter by GitHub user ownership
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

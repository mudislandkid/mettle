#!/usr/bin/env python3
"""
Batch Analysis Script for Code Counter

Analyzes all project folders within a directory and produces a consolidated report.

Usage:
    python batch_analyze.py /path/to/projects/directory [--output report.md] [--json results.json]
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional


# Sandboxed environment for any git subprocess we shell out to, so a hostile
# `.git/config` inside a scanned project can't trigger code execution.
_SAFE_GIT_ENV = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_OPTIONAL_LOCKS": "0",
    "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/local/bin"),
    "HOME": "/dev/null",
}

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from mettle.analyzers.code_analyzer import CodeAnalyzer
from mettle.analyzers.dependency_detection import detect_dependencies


# Known large public SDKs/frameworks that are typically vendored, not user projects
KNOWN_PUBLIC_SDKS = {
    'esp-idf', 'esp-adf', 'esp-mdf', 'esp-matter',  # Espressif
    'aws-sdk', 'azure-sdk', 'google-cloud-sdk',      # Cloud SDKs
    'tensorflow', 'pytorch', 'keras',                 # ML frameworks
    'react', 'angular', 'vue',                        # JS frameworks (if cloned)
    'linux', 'freebsd', 'zephyr',                     # OS kernels
    'llvm', 'gcc', 'clang',                           # Compilers
    'opencv', 'ffmpeg',                               # Media libraries
    'boost', 'abseil-cpp', 'folly',                   # C++ libraries
    'node', 'deno', 'bun',                            # Runtimes
    'micropython', 'circuitpython',                   # Embedded Python
    'arduino', 'platformio',                          # Embedded platforms
    'ros', 'ros2',                                    # Robotics
}


@dataclass
class ProjectSummary:
    """Summary metrics for a single project."""
    name: str
    total_dirs: int
    total_files: int
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    characters: int
    words: int
    functions: int
    classes: int
    todos: int
    imports: int
    languages: list
    avg_lines_per_file: float
    test_files: int = 0
    test_total_lines: int = 0
    test_code_lines: int = 0
    repo_url: Optional[str] = None
    last_commit_at: Optional[str] = None  # ISO-8601 with TZ, or None
    todo_items: list = None  # filled in __post_init__
    dependencies: list = None  # filled in __post_init__
    complex_functions: list = None  # filled in __post_init__
    # JS/TS-specific totals (zero unless the project contains relevant files).
    jsx_components: int = 0
    react_hooks: int = 0
    async_functions: int = 0
    interfaces: int = 0
    type_aliases: int = 0
    enums: int = 0

    def __post_init__(self):
        if self.todo_items is None:
            self.todo_items = []
        if self.dependencies is None:
            self.dependencies = []
        if self.complex_functions is None:
            self.complex_functions = []

    @property
    def code_percentage(self) -> float:
        if self.total_lines == 0:
            return 0
        return (self.code_lines / self.total_lines) * 100

    @property
    def test_percentage(self) -> float:
        """Test lines as a fraction of total lines (0-100)."""
        if self.total_lines == 0:
            return 0
        return (self.test_total_lines / self.total_lines) * 100

    @property
    def production_lines(self) -> int:
        """Total lines that are NOT in test files."""
        return max(0, self.total_lines - self.test_total_lines)

    @property
    def production_code_lines(self) -> int:
        """Code lines (non-blank, non-comment) that are NOT in test files."""
        return max(0, self.code_lines - self.test_code_lines)


# Common internal directory names that are usually NOT standalone projects
INTERNAL_FOLDER_NAMES = {
    # Source directories
    'src', 'source', 'lib', 'libs', 'core', 'app', 'apps',
    # Frontend/Backend splits
    'frontend', 'backend', 'client', 'server', 'web', 'api',
    # Common framework folders
    'src-tauri', 'electron', 'mobile', 'desktop',
    # Test/docs folders
    'tests', 'test', 'spec', 'specs', '__tests__', '__mocks__',
    'docs', 'documentation', 'doc',
    # Config/tooling folders
    'config', 'configs', 'scripts', 'tools', 'utils', 'utilities',
    'helpers', 'shared', 'common', 'types', 'interfaces',
    # Database/migration folders
    'prisma', 'migrations', 'alembic', 'supabase', 'database', 'db',
    # Build output / generated
    'htmlcov', 'coverage', 'reports', 'logs', 'tmp', 'temp',
    # Package managers
    'packages', 'modules', 'components', 'hooks', 'store', 'stores',
    # Research/data folders
    'research_docs', 'data', 'assets', 'public', 'static',
    # CI/CD
    'infrastructure', 'deploy', 'deployment', '.github',
    # Other common internal folders
    'legacy', 'archive', 'backup', 'examples', 'samples',
    'fixtures', 'mocks', 'stubs', 'factories',
    'middleware', 'services', 'controllers', 'models', 'views',
    'routes', 'handlers', 'resolvers', 'schemas', 'validators',
    'agents', 'workers', 'jobs', 'tasks', 'connectors', 'adapters',
    'plugins', 'extensions', 'addons', 'providers',
    'frontend-app', 'desktop-app', 'analyzer-worker', 'app-tests',
    'python-services', 'transcription-service', 'file-watcher',
    'test_scripts', 'proxy', 'knowledge', 'agent',
    # Vendored dependencies
    'esp-idf', 'esp-adf', 'managed_components',
}


def _git_remote_url(path: Path) -> Optional[str]:
    """Return the raw `origin` remote URL for a directory, or None."""
    if not (path / '.git').exists():
        return None
    try:
        result = subprocess.run(
            ['git', '-C', str(path), '--no-pager', 'remote', 'get-url', 'origin'],
            capture_output=True, text=True, timeout=5,
            env=_SAFE_GIT_ENV,
        )
        if result.returncode != 0:
            return None
        url = result.stdout.strip()
        return url or None
    except Exception:
        return None


def _git_last_commit_iso(path: Path) -> Optional[str]:
    """Return the most recent commit's author date in ISO-8601 form, or None."""
    if not (path / '.git').exists():
        return None
    try:
        result = subprocess.run(
            ['git', '-C', str(path), '--no-pager', 'log', '-1', '--format=%aI'],
            capture_output=True, text=True, timeout=5,
            env=_SAFE_GIT_ENV,
        )
        if result.returncode != 0:
            return None
        out = result.stdout.strip()
        return out or None
    except Exception:
        return None


def get_git_metadata(path: Path) -> dict:
    """Single call site for the git facts we cache on Project rows."""
    return {
        "repo_url": _git_remote_url(path),
        "last_commit_at": _git_last_commit_iso(path),
    }


def get_git_remote_owner(path: Path) -> Optional[str]:
    """Get the GitHub/GitLab username from the git remote URL."""
    url = _git_remote_url(path)
    if url is None:
        return None

    # SSH: git@github.com:username/repo.git
    # HTTPS: https://github.com/username/repo.git
    patterns = [
        r'git@(?:github|gitlab)\.com:([^/]+)/',
        r'https?://(?:github|gitlab)\.com/([^/]+)/',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1).lower()
    return None


def is_owned_by_user(path: Path, github_user: str) -> bool:
    """Check if the project's git remote is owned by the specified user."""
    owner = get_git_remote_owner(path)
    if owner is None:
        # No git remote - assume it's a local project (user's own)
        return True
    return owner.lower() == github_user.lower()


def is_known_public_sdk(path: Path) -> bool:
    """Check if the directory name matches a known public SDK."""
    return path.name.lower() in KNOWN_PUBLIC_SDKS


def is_project_directory(path: Path, include_internal: bool = False) -> bool:
    """Check if a directory looks like a project (has code files or common project markers)."""
    if not path.is_dir():
        return False

    # Skip hidden directories and common non-project folders
    if path.name.startswith('.'):
        return False

    # Directories to always skip - these are never standalone projects
    skip_names = {
        'node_modules', '__pycache__', 'venv', 'env', '.venv',
        'dist', 'build', 'target', '.git', '.svn', 'vendor',
        'coverage', '.next', '.nuxt', 'out', '.cache'
    }

    if path.name.lower() in skip_names:
        return False

    # Skip internal folder names unless explicitly included
    if not include_internal and path.name.lower() in INTERNAL_FOLDER_NAMES:
        return False

    # Check for common project indicators
    project_markers = [
        'package.json', 'pyproject.toml', 'setup.py', 'Cargo.toml',
        'go.mod', 'pom.xml', 'build.gradle', 'Makefile', 'CMakeLists.txt',
        'requirements.txt', 'Gemfile', 'composer.json', '.git'
    ]

    for marker in project_markers:
        if (path / marker).exists():
            return True

    # Check if directory contains code files
    code_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs', '.java', '.cpp', '.c', '.rb', '.php'}
    for item in path.iterdir():
        if item.is_file() and item.suffix.lower() in code_extensions:
            return True

    return False


def analyze_project(project_path: Path, analyzer: CodeAnalyzer) -> Optional[ProjectSummary]:
    """Analyze a single project and return summary metrics."""
    try:
        metrics = analyzer.analyze_directory(str(project_path))

        # Calculate totals from metrics_by_language
        total_lines = 0
        code_lines = 0
        comment_lines = 0
        blank_lines = 0
        characters = 0
        words = 0
        functions = 0
        classes = 0
        todos = 0
        imports = 0
        languages = []

        jsx_components = 0
        react_hooks = 0
        async_functions = 0
        interfaces = 0
        type_aliases = 0
        enums = 0

        for lang, file_metrics in metrics['metrics_by_language'].items():
            languages.append(lang)
            total_lines += file_metrics.total_lines
            code_lines += file_metrics.code_lines
            comment_lines += file_metrics.comment_lines
            blank_lines += file_metrics.blank_lines
            characters += file_metrics.characters
            words += file_metrics.words
            functions += file_metrics.functions
            classes += file_metrics.classes
            todos += file_metrics.todos
            imports += file_metrics.imports
            jsx_components += file_metrics.jsx_components
            react_hooks += file_metrics.react_hooks
            async_functions += file_metrics.async_functions
            interfaces += file_metrics.interfaces
            type_aliases += file_metrics.type_aliases
            enums += file_metrics.enums

        total_files = metrics['total_files']
        avg_lines = total_lines / total_files if total_files > 0 else 0

        git_meta = get_git_metadata(project_path)
        deps = detect_dependencies(project_path)

        return ProjectSummary(
            name=project_path.name,
            total_dirs=metrics['total_dirs'],
            total_files=total_files,
            total_lines=total_lines,
            code_lines=code_lines,
            comment_lines=comment_lines,
            blank_lines=blank_lines,
            characters=characters,
            words=words,
            functions=functions,
            classes=classes,
            todos=todos,
            imports=imports,
            languages=sorted(languages),
            avg_lines_per_file=round(avg_lines, 1),
            test_files=metrics.get('test_files', 0),
            test_total_lines=metrics.get('test_total_lines', 0),
            test_code_lines=metrics.get('test_code_lines', 0),
            repo_url=git_meta.get('repo_url'),
            last_commit_at=git_meta.get('last_commit_at'),
            todo_items=metrics.get('todo_items', []),
            dependencies=deps,
            complex_functions=metrics.get('complex_functions', []),
            jsx_components=jsx_components,
            react_hooks=react_hooks,
            async_functions=async_functions,
            interfaces=interfaces,
            type_aliases=type_aliases,
            enums=enums,
        )
    except Exception as e:
        console = Console()
        console.print(f"[yellow]Warning: Failed to analyze {project_path.name}: {e}[/yellow]")
        return None


def format_number(n: int) -> str:
    """Format number with thousands separator."""
    return f"{n:,}"


# Fields that get summed across projects for the totals tables. Adding a new
# total here automatically wires it into every report generator below.
_TOTAL_FIELDS = (
    'total_files',
    'total_lines',
    'code_lines',
    'comment_lines',
    'blank_lines',
    'functions',
    'classes',
    'todos',
    'imports',
    'test_files',
    'test_total_lines',
    'test_code_lines',
)


def compute_totals(summaries: list[ProjectSummary]) -> dict[str, int]:
    """Sum the headline metrics across every project (one pass, one place)."""
    totals = {field: 0 for field in _TOTAL_FIELDS}
    totals['total_projects'] = len(summaries)
    for s in summaries:
        for field in _TOTAL_FIELDS:
            totals[field] += getattr(s, field)
    totals['avg_lines_per_project'] = (
        totals['total_lines'] // totals['total_projects']
        if totals['total_projects'] > 0 else 0
    )
    # Tie-break sort by name so report ordering is deterministic between runs
    # for projects with identical line counts. Mutates in place — callers expect
    # the sorted list back too, so we don't return it.
    return totals


def _sorted_summaries(summaries: list[ProjectSummary]) -> list[ProjectSummary]:
    return sorted(summaries, key=lambda x: (-x.total_lines, x.name.lower()))


def generate_console_report(summaries: list[ProjectSummary], console: Console):
    """Generate and display console report."""
    summaries = _sorted_summaries(summaries)
    totals = compute_totals(summaries)

    table = Table(title="Project Analysis Summary", show_header=True, header_style="bold cyan")
    table.add_column("Project", style="bold")
    table.add_column("Files", justify="right")
    table.add_column("Total Lines", justify="right")
    table.add_column("Code Lines", justify="right")
    table.add_column("Code %", justify="right")
    table.add_column("Tests %", justify="right")
    table.add_column("Functions", justify="right")
    table.add_column("Classes", justify="right")
    table.add_column("Avg Lines/File", justify="right")
    table.add_column("Languages", max_width=30)

    for s in summaries:
        table.add_row(
            s.name,
            format_number(s.total_files),
            format_number(s.total_lines),
            format_number(s.code_lines),
            f"{s.code_percentage:.1f}%",
            f"{s.test_percentage:.1f}%",
            format_number(s.functions),
            format_number(s.classes),
            str(s.avg_lines_per_file),
            ", ".join(s.languages[:5]) + ("..." if len(s.languages) > 5 else "")
        )

    console.print()
    console.print(table)

    totals_table = Table(title="Overall Totals", show_header=True, header_style="bold green")
    totals_table.add_column("Metric", style="bold")
    totals_table.add_column("Value", justify="right")
    totals_table.add_row("Total Projects", format_number(totals['total_projects']))
    totals_table.add_row("Total Files", format_number(totals['total_files']))
    totals_table.add_row("Total Lines", format_number(totals['total_lines']))
    totals_table.add_row("Total Code Lines", format_number(totals['code_lines']))
    totals_table.add_row("Total Test Files", format_number(totals['test_files']))
    totals_table.add_row("Total Test Lines", format_number(totals['test_total_lines']))
    totals_table.add_row("Total Functions", format_number(totals['functions']))
    totals_table.add_row("Total Classes", format_number(totals['classes']))
    totals_table.add_row("Avg Lines/Project", format_number(totals['avg_lines_per_project']))

    console.print()
    console.print(totals_table)


def generate_markdown_report(summaries: list[ProjectSummary], output_path: Path):
    """Generate markdown report file."""
    summaries = _sorted_summaries(summaries)
    totals = compute_totals(summaries)

    lines = [
        "# Batch Code Analysis Report",
        "",
        f"**Projects Analyzed:** {totals['total_projects']}",
        "",
        "## Project Summary",
        "",
        "| Project | Files | Total Lines | Code Lines | Code % | Tests % | Functions | Classes | Avg Lines/File |",
        "|---------|------:|------------:|-----------:|-------:|--------:|----------:|--------:|---------------:|",
    ]

    for s in summaries:
        lines.append(
            f"| {s.name} | {s.total_files:,} | {s.total_lines:,} | {s.code_lines:,} | "
            f"{s.code_percentage:.1f}% | {s.test_percentage:.1f}% | {s.functions:,} | {s.classes:,} | {s.avg_lines_per_file} |"
        )

    lines.extend([
        "",
        "## Overall Totals",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| Total Projects | {totals['total_projects']:,} |",
        f"| Total Files | {totals['total_files']:,} |",
        f"| Total Lines | {totals['total_lines']:,} |",
        f"| Total Code Lines | {totals['code_lines']:,} |",
        f"| Total Test Files | {totals['test_files']:,} |",
        f"| Total Test Lines | {totals['test_total_lines']:,} |",
        f"| Total Functions | {totals['functions']:,} |",
        f"| Total Classes | {totals['classes']:,} |",
        "",
        "## Languages by Project",
        "",
    ])

    for s in summaries:
        lines.append(f"- **{s.name}**: {', '.join(s.languages)}")

    output_path.write_text("\n".join(lines))


def generate_json_report(summaries: list[ProjectSummary], output_path: Path):
    """Generate JSON report file."""
    summaries = _sorted_summaries(summaries)
    totals = compute_totals(summaries)

    data = {
        "projects": [asdict(s) for s in summaries],
        "totals": {
            "total_projects": totals['total_projects'],
            "total_files": totals['total_files'],
            "total_lines": totals['total_lines'],
            "total_code_lines": totals['code_lines'],
            "total_comment_lines": totals['comment_lines'],
            "total_blank_lines": totals['blank_lines'],
            "total_functions": totals['functions'],
            "total_classes": totals['classes'],
            "total_todos": totals['todos'],
            "total_imports": totals['imports'],
            "total_test_files": totals['test_files'],
            "total_test_lines": totals['test_total_lines'],
            "total_test_code_lines": totals['test_code_lines'],
        },
    }

    output_path.write_text(json.dumps(data, indent=2))


def main(args: argparse.Namespace | None = None) -> int:
    """Batch analyse projects under a parent directory.

    When invoked from Click (via ``mettle batch ...``), *args* is the Namespace
    constructed in ``mettle.cli``. When invoked directly
    (``python batch_analyze.py``), *args* is None and we parse sys.argv.
    """
    if args is None:
        parser = argparse.ArgumentParser(
            description="Analyze all project folders within a directory"
        )
        parser.add_argument(
            "directory",
            type=str,
            help="Parent directory containing project folders to analyze"
        )
        parser.add_argument(
            "--output", "-o",
            type=str,
            help="Output markdown report file path"
        )
        parser.add_argument(
            "--json", "-j",
            type=str,
            help="Output JSON report file path"
        )
        parser.add_argument(
            "--all", "-a",
            action="store_true",
            help="Analyze all subdirectories (not just detected projects)"
        )
        parser.add_argument(
            "--depth", "-d",
            type=int,
            default=1,
            help="Directory depth to search for projects (default: 1, recommended to keep at 1)"
        )
        parser.add_argument(
            "--include-internal",
            action="store_true",
            help="Include common internal folder names (src, lib, frontend, backend, etc.)"
        )
        parser.add_argument(
            "--github-user", "-u",
            type=str,
            help="Only include projects owned by this GitHub/GitLab username"
        )
        parser.add_argument(
            "--skip-public-sdks",
            action="store_true",
            help="Skip known public SDKs (esp-idf, tensorflow, etc.)"
        )
        parser.add_argument(
            "--max-files",
            type=int,
            default=0,
            help="Skip projects with more than this many files (0 = no limit, helps filter vendored SDKs)"
        )
        args = parser.parse_args()

    console = Console()
    parent_dir = Path(args.directory).resolve()

    if not parent_dir.exists():
        console.print(f"[red]Error: Directory not found: {parent_dir}[/red]")
        sys.exit(1)

    if not parent_dir.is_dir():
        console.print(f"[red]Error: Not a directory: {parent_dir}[/red]")
        sys.exit(1)

    # Find project directories
    console.print(f"\n[bold]Scanning for projects in:[/bold] {parent_dir}")

    if args.depth > 1:
        console.print(f"[yellow]Warning: Using depth={args.depth} may pick up internal folders. Consider using depth=1.[/yellow]")

    if args.depth == 1:
        subdirs = [d for d in parent_dir.iterdir() if d.is_dir() and not d.is_symlink()]
    else:
        # Deduplicate across depth iterations: the previous code glob'd at each
        # depth and concatenated, so a project at depth 1 would also be picked
        # up via its parent at depth 2 (and analyzed twice).
        seen: set[Path] = set()
        subdirs = []
        for depth in range(1, args.depth + 1):
            pattern = "/".join(["*"] * depth)
            for d in parent_dir.glob(pattern):
                if not d.is_dir() or d.is_symlink():
                    continue
                resolved = d.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                subdirs.append(d)

    if args.all:
        project_dirs = [d for d in subdirs if not d.name.startswith('.')]
    else:
        project_dirs = [d for d in subdirs if is_project_directory(d, args.include_internal)]

    # Filter out known public SDKs if requested
    if args.skip_public_sdks:
        before_count = len(project_dirs)
        project_dirs = [d for d in project_dirs if not is_known_public_sdk(d)]
        skipped = before_count - len(project_dirs)
        if skipped > 0:
            console.print(f"[dim]Skipped {skipped} known public SDK(s)[/dim]")

    # Filter by GitHub user ownership if specified
    if args.github_user:
        console.print(f"[dim]Filtering to projects owned by: {args.github_user}[/dim]")
        before_count = len(project_dirs)
        # Parallelize the per-project `git remote get-url` calls; the old
        # sequential version was up to ~5s × N projects.
        from concurrent.futures import ThreadPoolExecutor
        target_user = args.github_user.lower()
        with ThreadPoolExecutor(max_workers=min(16, max(4, len(project_dirs)))) as pool:
            owners = list(pool.map(get_git_remote_owner, project_dirs))
        project_dirs = [
            d for d, owner in zip(project_dirs, owners)
            if owner is None or owner.lower() == target_user
        ]
        skipped = before_count - len(project_dirs)
        if skipped > 0:
            console.print(f"[dim]Skipped {skipped} project(s) not owned by {args.github_user}[/dim]")

    if not project_dirs:
        console.print("[yellow]No project directories found.[/yellow]")
        sys.exit(0)

    console.print(f"[green]Found {len(project_dirs)} project(s) to analyze[/green]\n")

    # Analyze each project
    analyzer = CodeAnalyzer(debug=False)
    summaries: list[ProjectSummary] = []

    skipped_large = 0
    with console.status("[bold green]Analyzing projects...") as status:
        for i, project_dir in enumerate(sorted(project_dirs), 1):
            status.update(f"[bold green]Analyzing ({i}/{len(project_dirs)}): {project_dir.name}")

            summary = analyze_project(project_dir, analyzer)
            if summary and summary.total_files > 0:
                # Skip projects exceeding max_files threshold
                if args.max_files > 0 and summary.total_files > args.max_files:
                    skipped_large += 1
                    continue
                summaries.append(summary)

    if skipped_large > 0:
        console.print(f"[dim]Skipped {skipped_large} project(s) exceeding {args.max_files:,} files[/dim]")

    if not summaries:
        console.print("[yellow]No projects with analyzable files found.[/yellow]")
        sys.exit(0)

    # Generate reports
    generate_console_report(summaries, console)

    if args.output:
        output_path = Path(args.output)
        generate_markdown_report(summaries, output_path)
        console.print(f"\n[green]Markdown report saved to:[/green] {output_path}")

    if args.json:
        json_path = Path(args.json)
        generate_json_report(summaries, json_path)
        console.print(f"[green]JSON report saved to:[/green] {json_path}")

    return 0


if __name__ == "__main__":
    main()

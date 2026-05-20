#!/usr/bin/env python3

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel

from .analyzers.code_analyzer import CodeAnalyzer
from .reporters.console import ConsoleReporter
from .reporters.html import HTMLReporter
from .reporters.markdown import MarkdownReporter
from .reporters.pdf import PDFReporter


def get_project_name(directory_path: str, history: dict) -> str:
    """Get project name from user or use previous/default name.

    Args:
        directory_path: Path to the directory being analyzed
        history: Dictionary containing usage history

    Returns:
        Selected project name
    """
    default_name = os.path.basename(os.path.abspath(directory_path))

    # Check if we have a previous project name for this directory
    dir_key = str(Path(directory_path).resolve())
    previous_name = history.get("project_names", {}).get(dir_key)

    if previous_name:
        use_previous = questionary.confirm(
            f"Use previous project name '{previous_name}'?", default=True
        ).ask()

        if use_previous:
            return previous_name

    # If no previous name or user wants a new name
    choices = ["Enter new name"]

    # Add recent project names as choices
    recent_names = history.get("recent_projects", [])
    if recent_names:
        choices = [f"Use: {name}" for name in recent_names[:5]] + choices

    # Add default name as first choice if it's not in recent names
    if default_name not in recent_names:
        choices.insert(0, f"Use: {default_name}")

    name_choice = questionary.select("Choose project name", choices=choices).ask()

    if name_choice.startswith("Use: "):
        project_name = name_choice.removeprefix("Use: ")
    else:
        project_name = questionary.text(
            "Enter project name:", default=default_name, validate=lambda text: len(text) > 0
        ).ask()

    # Sanitize: strip path separators and parent-dir refs so a typed `..` or
    # `/foo` can't escape the analysis output directory.
    project_name = (project_name or "").replace(os.sep, "_").replace("/", "_").replace("\\", "_")
    project_name = project_name.strip(". ")
    if not project_name:
        project_name = default_name or "analysis"

    # Update history with the new project name
    if "project_names" not in history:
        history["project_names"] = {}
    history["project_names"][dir_key] = project_name

    # Update recent projects list
    if "recent_projects" not in history:
        history["recent_projects"] = []
    if project_name in history["recent_projects"]:
        history["recent_projects"].remove(project_name)
    history["recent_projects"].insert(0, project_name)
    history["recent_projects"] = history["recent_projects"][:10]  # Keep only last 10

    return project_name


def _state_base_dir() -> Path:
    """Where CLI state (analysis output, history) lives.

    Honours $METTLE_HOME for tests / web-backend callers, otherwise
    falls back to ~/.mettle so output isn't sprinkled wherever the user
    happened to be when they launched the tool.
    """
    override = os.environ.get("METTLE_HOME")
    if override:
        base = Path(override).expanduser()
    else:
        base = Path.home() / ".mettle"
    base.mkdir(parents=True, exist_ok=True)
    return base


def create_analysis_directory(project_name: str) -> Path:
    """Create a timestamped directory for analysis outputs."""
    base_dir = _state_base_dir() / "analysis"
    base_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    project_dir = base_dir / f"{timestamp}_{project_name}"
    project_dir.mkdir(exist_ok=True)

    return project_dir


def get_history_file() -> Path:
    """Get the path to the history file (under ~/.mettle)."""
    return _state_base_dir() / "history.json"


def load_history() -> dict:
    """Load history from file."""
    history_file = get_history_file()
    if history_file.exists():
        try:
            return json.loads(history_file.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def save_history(history: dict):
    """Save history to file."""
    history_file = get_history_file()
    history_file.write_text(json.dumps(history, indent=2))


def get_output_path(analysis_dir: Path, project_name: str, ext: str) -> Path:
    """Generate output path with automatic numbering if file exists."""
    base_path = analysis_dir / f"{project_name}_analysis{ext}"
    if not base_path.exists():
        return base_path

    # Bound the search so a pathological pre-existing tree can't infinite-loop.
    for counter in range(1, 10_000):
        new_path = analysis_dir / f"{project_name}_analysis_{counter}{ext}"
        if not new_path.exists():
            return new_path
    return analysis_dir / f"{project_name}_analysis_{datetime.now().strftime('%H%M%S%f')}{ext}"


def get_directory(history: dict) -> str:
    """Get directory to analyze through interactive prompts."""
    console = Console()

    while True:
        choices = ["Enter path"]
        if "last_path" in history:
            choices.insert(0, f"Last used: {history['last_path']}")

        path_choice = questionary.select("Choose directory to analyze", choices=choices).ask()

        if not path_choice:  # User pressed Ctrl+C
            raise KeyboardInterrupt

        if path_choice.startswith("Last used:"):
            path = history["last_path"]
        else:
            path = questionary.path("Enter the directory path", only_directories=True).ask()

        if not path:  # User pressed Ctrl+C
            raise KeyboardInterrupt

        if not os.path.isdir(path):
            console.print("[red]Error:[/red] Not a valid directory")
            continue

        # Save to history
        history["last_path"] = path
        return path


_CHECK_KEYS = {"file-lines-over", "functions-over", "cyclomatic-over", "todo-density-over"}


def _parse_fail_on(raw: list[str]) -> dict[str, int]:
    """Parse --fail-on KEY=VALUE pairs into a thresholds dict."""
    thresholds: dict[str, int] = {}
    for spec in raw:
        if "=" not in spec:
            raise ValueError(f"--fail-on expects KEY=VALUE, got {spec!r}")
        key, _, value = spec.partition("=")
        key = key.strip()
        if key not in _CHECK_KEYS:
            raise ValueError(f"unknown --fail-on key: {key!r}. valid: {sorted(_CHECK_KEYS)}")
        try:
            thresholds[key] = int(value.strip())
        except ValueError:
            raise ValueError(f"--fail-on {key} requires an integer, got {value!r}")
    return thresholds


def run_check_mode(args) -> int:
    """Non-interactive analysis with threshold checks; returns the exit code.

    Designed for `pre-commit` / CI: prints violations grouped by file, exits
    non-zero on the first failure. No prompts, no PDF, no history writes.
    """
    console = Console()

    if not args.directory:
        console.print("[red]--check requires a directory argument.[/red]")
        return 2

    try:
        thresholds = _parse_fail_on(args.fail_on)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        return 2

    if not thresholds:
        console.print(
            "[yellow]--check ran with no --fail-on thresholds; will only report counts.[/yellow]"
        )

    analyzer = CodeAnalyzer(
        debug=args.debug,
        max_lines=args.max_lines,
        exclude_types=args.exclude_types,
        exclude_dirs=args.exclude_dirs,
    )
    metrics = analyzer.analyze_directory(args.directory)

    violations: list[str] = []

    # file-lines-over: enumerate every file we analysed and compare its total_lines.
    file_lines_limit = thresholds.get("file-lines-over")
    if file_lines_limit is not None:
        for lang, files in analyzer.directory_analyzer.files_by_language.items():
            for path, fm in files.items():
                if fm.total_lines > file_lines_limit:
                    violations.append(
                        f"file-lines-over: {path} has {fm.total_lines} lines (limit {file_lines_limit})"
                    )

    # functions-over: same idea, but on per-file function count.
    functions_limit = thresholds.get("functions-over")
    if functions_limit is not None:
        for lang, files in analyzer.directory_analyzer.files_by_language.items():
            for path, fm in files.items():
                if fm.functions > functions_limit:
                    violations.append(
                        f"functions-over: {path} has {fm.functions} functions (limit {functions_limit})"
                    )

    # cyclomatic-over: Python AST analyzer captures per-function complexity.
    cyclomatic_limit = thresholds.get("cyclomatic-over")
    if cyclomatic_limit is not None:
        for entry in metrics.get("complex_functions", []):
            if entry["complexity"] > cyclomatic_limit:
                violations.append(
                    f"cyclomatic-over: {entry['qualname']} at {entry['file']}:{entry['line']} "
                    f"has complexity {entry['complexity']} (limit {cyclomatic_limit})"
                )

    # todo-density-over: project-level TODOs per 1k code lines.
    todo_density_limit = thresholds.get("todo-density-over")
    if todo_density_limit is not None:
        total_code = sum(fm.code_lines for fm in metrics["metrics_by_language"].values())
        total_todos = sum(fm.todos for fm in metrics["metrics_by_language"].values())
        if total_code > 0:
            density = (total_todos / total_code) * 1000
            if density > todo_density_limit:
                violations.append(
                    f"todo-density-over: project has {density:.1f} TODOs / 1k LOC (limit {todo_density_limit})"
                )

    # Print summary even when there are no thresholds — gives operators a
    # snapshot when wiring the command up for the first time.
    total_lines = sum(fm.total_lines for fm in metrics["metrics_by_language"].values())
    total_functions = sum(fm.functions for fm in metrics["metrics_by_language"].values())
    total_classes = sum(fm.classes for fm in metrics["metrics_by_language"].values())
    total_todos = sum(fm.todos for fm in metrics["metrics_by_language"].values())
    console.print(
        f"[dim]check: files={metrics['total_files']} lines={total_lines} "
        f"functions={total_functions} classes={total_classes} todos={total_todos}[/dim]"
    )

    if violations:
        for v in violations:
            console.print(f"[red]✖[/red] {v}")
        console.print(f"\n[bold red]{len(violations)} violation(s).[/bold red]")
        return 1

    if thresholds:
        console.print("[bold green]✓ All thresholds satisfied.[/bold green]")
    return 0


def _print_diff_against_last(console: Console, directory: str, metrics_path: Path) -> None:
    """Compare just-finished analysis to the most recent prior metrics.json
    for the same target directory."""
    base_dir = metrics_path.parent.parent  # ~/.mettle/analysis/
    target_resolved = str(Path(directory).resolve())

    # All prior run directories, newest first, excluding the one we just wrote.
    runs = sorted(
        [d for d in base_dir.iterdir() if d.is_dir() and d != metrics_path.parent],
        key=lambda d: d.name,
        reverse=True,
    )

    prev_metrics = None
    prev_run = None
    for run in runs:
        for jf in run.glob("*_metrics.json"):
            try:
                data = json.loads(jf.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            # Older snapshots may not carry the source dir; if so, accept the
            # most recent one as a best-effort.
            data_dir = data.get("source_directory")
            if data_dir is None or str(Path(data_dir).resolve()) == target_resolved:
                prev_metrics = data
                prev_run = run
                break
        if prev_metrics is not None:
            break

    if prev_metrics is None:
        console.print("\n[yellow]No previous analysis to diff against.[/yellow]")
        return

    current = json.loads(metrics_path.read_text())

    def _total(payload: dict, field: str) -> int:
        return sum(int(m.get(field, 0)) for m in payload.get("metrics_by_language", {}).values())

    fields = (
        "total_lines",
        "code_lines",
        "comment_lines",
        "blank_lines",
        "functions",
        "classes",
        "todos",
        "imports",
    )

    console.print(f"\n[bold]Diff vs {prev_run.name}:[/bold]")
    for field in fields:
        before = _total(prev_metrics, field)
        after = _total(current, field)
        delta = after - before
        if delta == 0:
            color = "dim"
            sign = " "
        elif delta > 0:
            color = "green" if field != "todos" else "red"
            sign = "+"
        else:
            color = "red" if field != "todos" else "green"
            sign = ""
        console.print(
            f"  {field:>16}: {before:>10,} → {after:>10,}   [{color}]{sign}{delta:,}[/{color}]"
        )


def main(args: argparse.Namespace | None = None) -> int:
    """Single-project scan entry point.

    When invoked from Click (via `mettle scan ...`), `args` is the Namespace
    constructed in `mettle.cli`. When invoked directly via `python -m
    mettle.__main__`, `args` is None and we parse sys.argv ourselves
    (preserves the old behaviour for tests).
    """
    if args is None:
        parser = argparse.ArgumentParser(description="Mettle - Analyze your codebase")
        parser.add_argument(
            "directory",
            nargs="?",
            help="Directory to analyze (optional, will prompt if not provided)",
        )
        parser.add_argument("-o", "--output", help="Output file path for PDF report")
        parser.add_argument("--no-pdf", action="store_true", help="Disable PDF report generation")
        parser.add_argument("--no-html", action="store_true", help="Disable HTML report generation")
        parser.add_argument(
            "--debug", action="store_true", help="Enable debug mode with additional logging"
        )
        parser.add_argument(
            "--max-lines",
            type=int,
            default=0,
            help="Skip files with more than this many lines (0 = no limit)",
        )
        parser.add_argument(
            "--exclude-types",
            nargs="+",
            help='Exclude specific file types (e.g., "Other" "Binary" "Data")',
        )
        parser.add_argument(
            "--exclude-dirs",
            nargs="+",
            help='Exclude specific directories (e.g., "models" "node_modules")',
        )
        parser.add_argument(
            "--compare-to-last",
            action="store_true",
            help="After analysis, print a diff against the most recent prior run for this directory.",
        )
        parser.add_argument(
            "--check",
            action="store_true",
            help="Non-interactive lint-style mode. Skips prompts and PDF, exits non-zero on threshold violations.",
        )
        parser.add_argument(
            "--fail-on",
            action="append",
            metavar="KEY=VALUE",
            default=[],
            help="Threshold for --check (repeatable). Keys: file-lines-over, functions-over, "
            "cyclomatic-over, todo-density-over. Example: --fail-on file-lines-over=500",
        )
        parser.add_argument(
            "--watch",
            action="store_true",
            help="Watch the directory and re-analyze on file changes. Requires the [watch] extra.",
        )
        parser.add_argument(
            "--watch-debounce",
            type=int,
            default=1500,
            help="Debounce window (ms) between bursts of file changes when --watch is on (default: 1500).",
        )
        args = parser.parse_args()

    if args.check and args.watch:
        Console().print("[red]--check and --watch are mutually exclusive.[/red]")
        sys.exit(2)

    if args.check:
        sys.exit(run_check_mode(args))

    if args.watch:
        from .watch import run_watch

        sys.exit(run_watch(args, Console()))
    console = Console()

    try:
        # Show welcome message
        console.print(
            Panel.fit(
                "[bold blue]Code Counter[/bold blue]\n"
                "[cyan]A powerful and extensible code analysis tool[/cyan]",
                border_style="blue",
            )
        )
        console.print()

        # Load history
        history = load_history()

        # Get directory - either from command line or interactive prompt
        directory = args.directory if args.directory else get_directory(history)

        # Save updated history
        save_history(history)

        # Get project name
        project_name = get_project_name(directory, history)

        # Create analysis directory
        analysis_dir = create_analysis_directory(project_name)
        console.print(f"\nAnalysis files will be saved in: [blue]{analysis_dir}[/blue]\n")

        # Initialize analyzer
        analyzer = CodeAnalyzer(
            debug=args.debug,
            max_lines=args.max_lines,
            exclude_types=args.exclude_types,
            exclude_dirs=args.exclude_dirs,
        )

        # Analyze the directory
        with console.status("[bold green]Analyzing code..."):
            metrics = analyzer.analyze_directory(directory)

        # Generate reports
        console_reporter = ConsoleReporter(
            metrics_by_language=metrics["metrics_by_language"],
            language_stats=metrics["language_stats"],
            total_files=metrics["total_files"],
            total_dirs=metrics["total_dirs"],
            largest_line_files=metrics["largest_line_files"],
        )
        console_reporter.generate_report()

        # PDF report (optional)
        if not args.no_pdf:
            pdf_path = args.output if args.output else analysis_dir / f"{project_name}_analysis.pdf"
            pdf_reporter = PDFReporter(
                metrics_by_language=metrics["metrics_by_language"],
                language_stats=metrics["language_stats"],
                total_files=metrics["total_files"],
                total_dirs=metrics["total_dirs"],
                largest_line_files=metrics["largest_line_files"],
            )
            pdf_reporter.generate_report(str(pdf_path))
            console.print(f"\nPDF report saved to: [blue]{pdf_path}[/blue]")

        # Markdown report
        markdown_path = analysis_dir / f"{project_name}_analysis.md"
        markdown_reporter = MarkdownReporter(
            metrics_by_language=metrics["metrics_by_language"],
            language_stats=metrics["language_stats"],
            total_files=metrics["total_files"],
            total_dirs=metrics["total_dirs"],
            largest_line_files=metrics["largest_line_files"],
            project_name=project_name,
        )
        markdown_reporter.generate_report(str(markdown_path))
        console.print(f"Markdown report saved to: [blue]{markdown_path}[/blue]")

        # HTML report (self-contained, shareable)
        if not args.no_html:
            html_path = analysis_dir / f"{project_name}_analysis.html"
            html_reporter = HTMLReporter(
                metrics_by_language=metrics["metrics_by_language"],
                language_stats=metrics["language_stats"],
                total_files=metrics["total_files"],
                total_dirs=metrics["total_dirs"],
                largest_line_files=metrics["largest_line_files"],
                project_name=project_name,
            )
            html_reporter.generate_report(str(html_path))
            console.print(f"HTML report saved to: [blue]{html_path}[/blue]")

        # Save raw metrics data for potential future use
        metrics_path = analysis_dir / f"{project_name}_metrics.json"
        analyzer.save_metrics(metrics_path)

        if args.compare_to_last:
            _print_diff_against_last(console, directory, metrics_path)

        console.print("\n[bold green]Analysis complete![/bold green]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Analysis cancelled by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        # `console` is bound on entry, so this can't UnboundLocalError.
        import traceback

        console.print(f"\n[red]Error: {e}[/red]")
        if args.debug:
            console.print(traceback.format_exc())
        sys.exit(1)

    return 0


if __name__ == "__main__":
    from .cli import cli

    cli()

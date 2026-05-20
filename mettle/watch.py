"""Watch mode — re-run analysis on file changes and print deltas.

Triggered via `code-counter --watch /path`. Uses `watchfiles` (optional dep
installed via `pip install -e ".[watch]"`). Filters out the same directories
that DirectoryAnalyzer would skip, debounces bursts, and prints a compact
delta vs the previous run.
"""

from __future__ import annotations

import os
from pathlib import Path

from rich.console import Console

from .analyzers.code_analyzer import CodeAnalyzer

_TRACKED_FIELDS = (
    "total_files",
    "total_lines",
    "code_lines",
    "comment_lines",
    "blank_lines",
    "functions",
    "classes",
    "todos",
    "imports",
)


def _aggregate_totals(metrics: dict) -> dict[str, int]:
    """Reduce the analyzer's per-language metrics into the flat totals we diff."""
    by_lang = metrics.get("metrics_by_language", {})
    totals: dict[str, int] = {"total_files": int(metrics.get("total_files", 0))}
    for field in _TRACKED_FIELDS:
        if field == "total_files":
            continue
        totals[field] = sum(getattr(m, field, 0) for m in by_lang.values())
    return totals


def _print_totals(console: Console, totals: dict[str, int]) -> None:
    parts = [f"{field}={totals.get(field, 0):,}" for field in _TRACKED_FIELDS]
    console.print(f"[dim]  {'  '.join(parts)}[/dim]")


def _print_delta(console: Console, before: dict[str, int], after: dict[str, int]) -> None:
    """Compact one-line-per-changed-metric delta. Silent when nothing moved."""
    moved = False
    for field in _TRACKED_FIELDS:
        b = before.get(field, 0)
        a = after.get(field, 0)
        if a == b:
            continue
        moved = True
        delta = a - b
        # TODO is the one metric where "more" is bad — invert the colour.
        if field == "todos":
            colour = "red" if delta > 0 else "green"
        else:
            colour = "green" if delta > 0 else "red"
        sign = "+" if delta > 0 else ""
        console.print(f"  {field:>14}: {b:>10,} → {a:>10,}   [{colour}]{sign}{delta:,}[/{colour}]")
    if not moved:
        console.print("[dim]  (no metric changes)[/dim]")


def _make_change_filter(analyzer: CodeAnalyzer) -> Callable[[Change, str], bool]:
    """Return a watchfiles change filter that drops paths inside excluded dirs.

    Imported lazily so this module doesn't blow up at import time when
    watchfiles isn't installed.
    """
    from watchfiles import Change, DefaultFilter

    excluded_dirs = analyzer.directory_analyzer._excluded_dir_set()

    class _Filter(DefaultFilter):
        # Mirror DirectoryAnalyzer.is_excluded() exactly so we don't trigger
        # re-runs for changes inside .git, node_modules, etc.
        def __call__(self, change: Change, path: str) -> bool:
            norm = path.replace("\\", "/")
            for part in norm.split("/"):
                if part in excluded_dirs:
                    return False
            return super().__call__(change, path)

    return _Filter()


def run_watch(args, console: Console) -> int:
    """Watch mode entry point. Returns an exit code."""
    try:
        from watchfiles import watch
    except ImportError:
        console.print(
            "[red]--watch requires the watchfiles package.[/red]\n"
            '[yellow]Install it with:[/yellow] pip install -e ".[watch]"  '
            "[dim](or:[/dim] pip install watchfiles[dim])[/dim]"
        )
        return 2

    if not args.directory:
        console.print("[red]--watch requires a directory argument.[/red]")
        return 2

    target = Path(args.directory).expanduser().resolve()
    if not target.is_dir():
        console.print(f"[red]Not a directory:[/red] {target}")
        return 2

    analyzer = CodeAnalyzer(
        debug=args.debug,
        max_lines=args.max_lines,
        exclude_types=args.exclude_types,
        exclude_dirs=args.exclude_dirs,
    )

    debounce_ms = max(200, int(getattr(args, "watch_debounce", 1500)))

    console.print(
        f"[bold]Watching[/bold] [blue]{target}[/blue]  [dim](debounce {debounce_ms}ms — Ctrl+C to stop)[/dim]"
    )

    # Initial baseline analysis.
    initial = analyzer.analyze_directory(str(target))
    baseline = _aggregate_totals(initial)
    console.print("[bold]Initial scan:[/bold]")
    _print_totals(console, baseline)

    change_filter = _make_change_filter(analyzer)

    try:
        for changes in watch(
            str(target),
            watch_filter=change_filter,
            debounce=debounce_ms,
            recursive=True,
            yield_on_timeout=False,
        ):
            # Print a compact preview of what triggered the run.
            preview = list(changes)[:3]
            extra = len(changes) - len(preview)
            paths = ", ".join(os.path.relpath(p, str(target)) for _, p in preview)
            if extra > 0:
                paths += f" (+{extra} more)"
            console.print(f"\n[cyan]changes:[/cyan] {paths}")

            # Re-run analysis. A new CodeAnalyzer keeps state clean between ticks.
            tick_analyzer = CodeAnalyzer(
                debug=args.debug,
                max_lines=args.max_lines,
                exclude_types=args.exclude_types,
                exclude_dirs=args.exclude_dirs,
            )
            current = tick_analyzer.analyze_directory(str(target))
            totals = _aggregate_totals(current)
            _print_delta(console, baseline, totals)
            baseline = totals
    except KeyboardInterrupt:
        console.print("\n[yellow]Watch stopped.[/yellow]")
        return 0
    except Exception as exc:  # surfaced rather than silently dropping
        console.print(f"[red]Watch error:[/red] {exc}")
        return 1

    return 0

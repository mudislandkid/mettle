"""Mettle CLI — Click command tree.

Subcommands:
    scan       Analyze a single project directory.
    batch      Analyze many projects under a parent directory.
    watch      Watch a directory and re-analyze on file changes.
    check      Non-interactive lint-style mode with threshold gating.
    web        Launch the web UI (CLI + backend + frontend).

Each subcommand delegates to the existing implementation modules so this
file stays small and the surface is testable. Argparse-based handlers are
wrapped with `click.pass_context` boundaries; the implementations consume
their own `argparse.Namespace` shaped objects via `_ns_from_kwargs()`.
"""
from __future__ import annotations

import argparse
import sys

import click

from . import __version__


def _ns_from_kwargs(**kwargs) -> argparse.Namespace:
    """Convert Click's kwargs into the Namespace shape expected by the
    pre-existing argparse handlers (scan, check, watch)."""
    return argparse.Namespace(**kwargs)


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    invoke_without_command=False,
)
@click.version_option(version=__version__, prog_name="mettle")
def cli() -> None:
    """Mettle — triage dashboard for the AI-coding era.

    Run `mettle <subcommand> --help` for per-command flags.
    """


# ---------------------------------------------------------------- scan
@cli.command()
@click.argument("directory", required=False)
@click.option("-o", "--output", help="Output file path for PDF report.")
@click.option("--no-pdf", is_flag=True, help="Disable PDF report generation.")
@click.option("--no-html", is_flag=True, help="Disable HTML report generation.")
@click.option("--debug", is_flag=True, help="Enable debug logging.")
@click.option("--max-lines", type=int, default=0, help="Skip files larger than N lines (0 = no limit).")
@click.option("--exclude-types", multiple=True, help="Exclude file types (repeatable).")
@click.option("--exclude-dirs", multiple=True, help="Exclude directories (repeatable).")
@click.option("--compare-to-last", is_flag=True, help="Diff against the most recent prior run.")
def scan(
    directory: str | None,
    output: str | None,
    no_pdf: bool,
    no_html: bool,
    debug: bool,
    max_lines: int,
    exclude_types: tuple[str, ...],
    exclude_dirs: tuple[str, ...],
    compare_to_last: bool,
) -> None:
    """Analyze a single project directory."""
    from .__main__ import main as _scan_main

    ns = _ns_from_kwargs(
        directory=directory,
        output=output,
        no_pdf=no_pdf,
        no_html=no_html,
        debug=debug,
        max_lines=max_lines,
        exclude_types=list(exclude_types) if exclude_types else None,
        exclude_dirs=list(exclude_dirs) if exclude_dirs else None,
        compare_to_last=compare_to_last,
        check=False,
        fail_on=[],
        watch=False,
        watch_debounce=1500,
    )
    sys.exit(_scan_main(ns) or 0)


# --------------------------------------------------------------- batch
@cli.command()
@click.argument("parent_dir")
@click.option("--depth", type=int, default=1, help="How many levels under PARENT_DIR to search.")
@click.option("--github-user", help="Only include projects whose git remote owner matches.")
@click.option("--skip-public-sdks", is_flag=True, default=True, help="Skip well-known public SDKs.")
@click.option("--max-files", type=int, default=10000, help="Cap files per project.")
@click.option("--include-internal", is_flag=True, help="Include vendored/internal directories.")
@click.option("--all", "all_projects", is_flag=True, help="No owner filter.")
@click.option("-o", "--output", help="JSON output path.")
@click.option("-m", "--markdown", help="Markdown report output path.")
def batch(
    parent_dir: str,
    depth: int,
    github_user: str | None,
    skip_public_sdks: bool,
    max_files: int,
    include_internal: bool,
    all_projects: bool,
    output: str | None,
    markdown: str | None,
) -> None:
    """Analyze many projects under PARENT_DIR."""
    import batch_analyze

    ns = _ns_from_kwargs(
        parent_dir=parent_dir,
        depth=depth,
        github_user=github_user,
        skip_public_sdks=skip_public_sdks,
        max_files=max_files,
        include_internal=include_internal,
        all=all_projects,
        output=output,
        markdown=markdown,
    )
    sys.exit(batch_analyze.main(ns) or 0)


# --------------------------------------------------------------- watch
@cli.command()
@click.argument("directory")
@click.option("--watch-debounce", type=int, default=1500, help="Debounce window in ms.")
def watch(directory: str, watch_debounce: int) -> None:
    """Watch a directory and re-run analysis on file changes."""
    from rich.console import Console
    from .watch import run_watch

    ns = _ns_from_kwargs(
        directory=directory,
        watch=True,
        watch_debounce=watch_debounce,
        debug=False,
        no_pdf=True,
        no_html=True,
        output=None,
        max_lines=0,
        exclude_types=None,
        exclude_dirs=None,
        compare_to_last=False,
        check=False,
        fail_on=[],
    )
    sys.exit(run_watch(ns, Console()))


# --------------------------------------------------------------- check
@cli.command()
@click.argument("directory")
@click.option(
    "--fail-on",
    multiple=True,
    metavar="KEY=VALUE",
    help="Threshold for --check. Keys: file-lines-over, functions-over, "
    "cyclomatic-over, todo-density-over. Repeatable.",
)
@click.option("--exclude-dirs", multiple=True, help="Exclude directories (repeatable).")
@click.option("--exclude-types", multiple=True, help="Exclude file types (repeatable).")
def check(
    directory: str,
    fail_on: tuple[str, ...],
    exclude_dirs: tuple[str, ...],
    exclude_types: tuple[str, ...],
) -> None:
    """Non-interactive lint-style mode."""
    from .__main__ import run_check_mode

    ns = _ns_from_kwargs(
        directory=directory,
        fail_on=list(fail_on),
        exclude_dirs=list(exclude_dirs) if exclude_dirs else None,
        exclude_types=list(exclude_types) if exclude_types else None,
        check=True,
        debug=False,
        max_lines=0,
        no_pdf=True,
        no_html=True,
        output=None,
        compare_to_last=False,
        watch=False,
        watch_debounce=1500,
    )
    sys.exit(run_check_mode(ns))


# ----------------------------------------------------------------- web
@cli.command()
@click.option("--mode", type=click.Choice(["dev", "prod", "backend-only"]), default="dev")
@click.option("--backend-host", default="127.0.0.1")
@click.option("--backend-port", type=int, default=8000)
@click.option("--frontend-port", type=int, default=5173)
@click.option("--skip-install", is_flag=True)
@click.option("--auto-install", is_flag=True)
def web(
    mode: str,
    backend_host: str,
    backend_port: int,
    frontend_port: int,
    skip_install: bool,
    auto_install: bool,
) -> None:
    """Launch the Mettle web UI."""
    # web/run.py is a top-level script outside the package; import it via
    # sys.path manipulation in a tightly-scoped block.
    import sys as _sys
    from pathlib import Path as _Path

    web_dir = _Path(__file__).resolve().parent.parent / "web"
    _sys.path.insert(0, str(web_dir))
    try:
        import run as _web_run  # type: ignore[import-not-found]
    finally:
        _sys.path.pop(0)

    ns = _ns_from_kwargs(
        mode=mode,
        backend_host=backend_host,
        backend_port=backend_port,
        frontend_port=frontend_port,
        skip_install=skip_install,
        auto_install=auto_install,
    )
    _sys.exit(_web_run.main(ns) or 0)


if __name__ == "__main__":  # pragma: no cover
    cli()

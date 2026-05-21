"""Export API routes."""

import csv
import json
from io import StringIO

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import PlainTextResponse

# Characters Excel / Google Sheets / LibreOffice will treat as the start of a
# formula if they appear at the very beginning of a cell. Wrapping such cells
# with a leading apostrophe is the OWASP-recommended mitigation.
_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _safe_cell(value: object) -> str:
    """Return a string safe to drop into a CSV cell."""
    s = "" if value is None else str(value)
    if s and s[0] in _CSV_FORMULA_PREFIXES:
        # A leading apostrophe forces text mode in every major spreadsheet.
        return "'" + s
    return s


from sqlmodel import Session, select

from ..database.connection import get_session
from ..database.models import Analysis, Project, RecentPath
from ..schemas.common import PathValidation, RecentPathResponse
from ..services.analyzer_service import validate_directory

router = APIRouter()


@router.get("/export/markdown/{analysis_id}")
async def export_markdown(analysis_id: int, session: Session = Depends(get_session)):
    """Export analysis as Markdown."""
    analysis = session.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    projects = session.exec(
        select(Project)
        .where(Project.analysis_id == analysis_id)
        .order_by(Project.total_lines.desc())
    ).all()

    # Generate markdown
    lines = [
        "# Batch Code Analysis Report",
        "",
        f"**Directory:** {analysis.directory_path}",
        f"**Analyzed:** {analysis.analyzed_at.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Projects Analyzed:** {len(projects)}",
        "",
        "## Project Summary",
        "",
        "| Project | Files | Total Lines | Code Lines | Code % | Functions | Classes | Avg Lines/File |",
        "|---------|------:|------------:|-----------:|-------:|----------:|--------:|---------------:|",
    ]

    for p in projects:
        code_pct = (p.code_lines / p.total_lines * 100) if p.total_lines > 0 else 0
        lines.append(
            f"| {p.name} | {p.total_files:,} | {p.total_lines:,} | {p.code_lines:,} | "
            f"{code_pct:.1f}% | {p.functions:,} | {p.classes:,} | {p.avg_lines_per_file} |"
        )

    # Totals
    total_files = sum(p.total_files for p in projects)
    total_lines = sum(p.total_lines for p in projects)
    total_code = sum(p.code_lines for p in projects)
    total_functions = sum(p.functions for p in projects)
    total_classes = sum(p.classes for p in projects)

    lines.extend(
        [
            "",
            "## Overall Totals",
            "",
            "| Metric | Value |",
            "|--------|------:|",
            f"| Total Projects | {len(projects):,} |",
            f"| Total Files | {total_files:,} |",
            f"| Total Lines | {total_lines:,} |",
            f"| Total Code Lines | {total_code:,} |",
            f"| Total Functions | {total_functions:,} |",
            f"| Total Classes | {total_classes:,} |",
            "",
            "## Languages by Project",
            "",
        ]
    )

    for p in projects:
        langs = ", ".join(p.languages) if p.languages else "Unknown"
        lines.append(f"- **{p.name}**: {langs}")

    content = "\n".join(lines)

    return PlainTextResponse(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=analysis_{analysis_id}.md"},
    )


@router.get("/export/json/{analysis_id}")
async def export_json(analysis_id: int, session: Session = Depends(get_session)):
    """Export analysis as JSON."""
    analysis = session.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    projects = session.exec(
        select(Project)
        .where(Project.analysis_id == analysis_id)
        .order_by(Project.total_lines.desc())
    ).all()

    data = {
        "analysis": {
            "id": analysis.id,
            "directory_path": analysis.directory_path,
            "analyzed_at": analysis.analyzed_at.isoformat(),
            "status": analysis.status,
            "filters_applied": analysis.filters_applied,
        },
        "projects": [
            {
                "name": p.name,
                "path": p.path,
                "total_dirs": p.total_dirs,
                "total_files": p.total_files,
                "total_lines": p.total_lines,
                "code_lines": p.code_lines,
                "comment_lines": p.comment_lines,
                "blank_lines": p.blank_lines,
                "characters": p.characters,
                "words": p.words,
                "functions": p.functions,
                "classes": p.classes,
                "todos": p.todos,
                "imports": p.imports,
                "languages": p.languages,
                "avg_lines_per_file": p.avg_lines_per_file,
                "code_percentage": (p.code_lines / p.total_lines * 100) if p.total_lines > 0 else 0,
                "flags": [f.flag_type for f in p.flags],
                "tags": [pt.tag.name for pt in p.project_tags],
            }
            for p in projects
        ],
        "totals": {
            "total_projects": len(projects),
            "total_files": sum(p.total_files for p in projects),
            "total_lines": sum(p.total_lines for p in projects),
            "total_code_lines": sum(p.code_lines for p in projects),
            "total_functions": sum(p.functions for p in projects),
            "total_classes": sum(p.classes for p in projects),
        },
    }

    content = json.dumps(data, indent=2)

    return PlainTextResponse(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=analysis_{analysis_id}.json"},
    )


@router.get("/export/csv/{analysis_id}")
async def export_csv(analysis_id: int, session: Session = Depends(get_session)):
    """Export analysis as CSV."""
    analysis = session.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    projects = session.exec(
        select(Project)
        .where(Project.analysis_id == analysis_id)
        .order_by(Project.total_lines.desc())
    ).all()

    # Build CSV using the stdlib csv module: handles embedded quotes, commas,
    # and newlines correctly per RFC 4180. We additionally guard every cell
    # against spreadsheet formula injection via `_safe_cell`.
    output = StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    headers = [
        "Name",
        "Path",
        "Directories",
        "Files",
        "Total Lines",
        "Code Lines",
        "Comment Lines",
        "Blank Lines",
        "Code %",
        "Functions",
        "Classes",
        "TODOs",
        "Imports",
        "Avg Lines/File",
        "Languages",
        "Flags",
        "Tags",
    ]
    writer.writerow(headers)

    for p in projects:
        code_pct = (p.code_lines / p.total_lines * 100) if p.total_lines > 0 else 0
        langs = "|".join(p.languages) if p.languages else ""
        flags = "|".join(f.flag_type for f in p.flags)
        tags = "|".join(pt.tag.name for pt in p.project_tags)

        writer.writerow(
            [
                _safe_cell(p.name),
                _safe_cell(p.path),
                p.total_dirs,
                p.total_files,
                p.total_lines,
                p.code_lines,
                p.comment_lines,
                p.blank_lines,
                f"{code_pct:.1f}",
                p.functions,
                p.classes,
                p.todos,
                p.imports,
                p.avg_lines_per_file,
                _safe_cell(langs),
                _safe_cell(flags),
                _safe_cell(tags),
            ]
        )

    content = output.getvalue()

    return PlainTextResponse(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=analysis_{analysis_id}.csv"},
    )


# Utility endpoints
@router.post("/validate-path", response_model=PathValidation)
async def validate_path(payload: dict = Body(...)):
    """Validate a directory path."""
    from web.backend.security.path_jail import PathJailError, resolve_and_check

    path = payload.get("path", "")
    if not isinstance(path, str):
        raise HTTPException(status_code=400, detail="path must be a string")
    try:
        resolve_and_check(path)
    except PathJailError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return validate_directory(path)


@router.get("/recent-paths", response_model=list[RecentPathResponse])
async def get_recent_paths(
    limit: int = 10,
    session: Session = Depends(get_session),
):
    """Get recently used directory paths.

    Paths outside the configured METTLE_SCAN_ROOTS are silently filtered out
    so stale DB entries from a previous configuration don't leak. The list shrinks;
    no error is surfaced.
    """
    from web.backend.security import settings
    from web.backend.security.path_jail import PathJailError, resolve_and_check

    rows = session.exec(select(RecentPath).order_by(RecentPath.last_used.desc()).limit(limit)).all()

    if settings.scan_roots() is None:
        return rows

    # Filter row-by-row to preserve the original DB string (resolve_and_check
    # canonicalises the path, so comparing resolved → raw doesn't round-trip).
    survivors = []
    for r in rows:
        try:
            resolve_and_check(r.path)
        except PathJailError:
            continue
        survivors.append(r)
    return survivors

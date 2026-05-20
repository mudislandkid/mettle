"""Project API routes."""

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..database.connection import get_session
from ..database.models import (
    FLAG_TYPES,
    Analysis,
    Project,
    ProjectFlag,
    ProjectNote,
    ProjectTag,
    Tag,
)
from ..schemas.analysis import (
    DependencyUsage,
    DependencyUsageResponse,
    HealthComponentResponse,
    HealthResponse,
    ProjectCompareEntry,
    ProjectCompareResponse,
    ProjectDiffEntry,
    ProjectDiffResponse,
    ProjectHighlight,
    ProjectHighlightsResponse,
    ProjectMetricsSnapshot,
    ProjectNoteUpdate,
    ProjectResponse,
)
from ..schemas.tags import (
    BulkFlagRequest,
    BulkResult,
    BulkTagRequest,
    ProjectFlagUpdate,
)
from ..services.analyzer_service import AnalyzerService
from ..services.health_score import compute_health

router = APIRouter()


def _get_note_text(session: Session, path: str) -> str:
    note = session.get(ProjectNote, path)
    return note.notes if note else ""


def get_project_response(project: Project, session: Session | None = None) -> ProjectResponse:
    """Convert a Project model to ProjectResponse, attaching notes if a session is given."""
    code_pct = (project.code_lines / project.total_lines * 100) if project.total_lines > 0 else 0
    test_pct = (
        (project.test_total_lines / project.total_lines * 100) if project.total_lines > 0 else 0
    )
    flags = [f.flag_type for f in project.flags]
    tags = [
        {"id": pt.tag.id, "name": pt.tag.name, "color": pt.tag.color} for pt in project.project_tags
    ]
    notes = _get_note_text(session, project.path) if session is not None else ""

    return ProjectResponse(
        id=project.id,
        analysis_id=project.analysis_id,
        name=project.name,
        path=project.path,
        total_dirs=project.total_dirs,
        total_files=project.total_files,
        total_lines=project.total_lines,
        code_lines=project.code_lines,
        comment_lines=project.comment_lines,
        blank_lines=project.blank_lines,
        characters=project.characters,
        words=project.words,
        functions=project.functions,
        classes=project.classes,
        todos=project.todos,
        imports=project.imports,
        languages=project.languages,
        avg_lines_per_file=project.avg_lines_per_file,
        code_percentage=code_pct,
        test_files=project.test_files,
        test_total_lines=project.test_total_lines,
        test_code_lines=project.test_code_lines,
        test_percentage=test_pct,
        repo_url=project.repo_url,
        last_commit_at=project.last_commit_at,
        health_score=compute_health(project).score,
        todo_items=project.todo_items or [],
        dependencies=project.dependencies or [],
        complex_functions=project.complex_functions or [],
        jsx_components=project.jsx_components,
        react_hooks=project.react_hooks,
        async_functions=project.async_functions,
        interfaces=project.interfaces,
        type_aliases=project.type_aliases,
        enums=project.enums,
        notes=notes,
        flags=flags,
        tags=tags,
    )


# Columns whitelisted for `sort_by`. Avoids letting clients sort by arbitrary
# attribute names (which would either explode or leak schema details).
_SORTABLE_COLUMNS = frozenset(
    {
        "name",
        "path",
        "total_files",
        "total_lines",
        "code_lines",
        "comment_lines",
        "blank_lines",
        "functions",
        "classes",
        "todos",
        "imports",
        "avg_lines_per_file",
        "test_total_lines",
        "test_code_lines",
        "last_commit_at",
    }
)


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    analysis_id: int | None = Query(None, description="Filter by analysis ID"),
    flag: str | None = Query(None, description="Filter by flag type"),
    tag: str | None = Query(None, description="Filter by tag name"),
    exclude_flag: str | None = Query(None, description="Exclude projects with this flag"),
    search: str | None = Query(None, description="Search project name"),
    stale_days: int | None = Query(
        None,
        ge=1,
        le=3650,
        description="Only return projects whose last commit is older than this many days (or has no commit at all)",
    ),
    sort_by: str = Query("total_lines", description="Sort by field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    """List projects with filtering and sorting."""
    query = select(Project)

    # Filter by analysis
    if analysis_id:
        query = query.where(Project.analysis_id == analysis_id)

    # Filter by flag
    if flag:
        query = query.join(ProjectFlag).where(ProjectFlag.flag_type == flag)

    # Exclude by flag
    if exclude_flag:
        excluded_ids = select(ProjectFlag.project_id).where(ProjectFlag.flag_type == exclude_flag)
        query = query.where(Project.id.not_in(excluded_ids))

    # Filter by tag
    if tag:
        query = query.join(ProjectTag).join(Tag).where(Tag.name == tag)

    # Search by name
    if search:
        query = query.where(Project.name.ilike(f"%{search}%"))

    # Stale filter: last commit older than N days (or unknown). Excludes
    # explicitly-archived projects since those are intentionally inactive.
    if stale_days is not None:
        from sqlalchemy import or_

        cutoff = datetime.now(timezone.utc) - timedelta(days=stale_days)
        archived_ids = select(ProjectFlag.project_id).where(ProjectFlag.flag_type == "archived")
        query = query.where(
            or_(Project.last_commit_at == None, Project.last_commit_at < cutoff)  # noqa: E711
        ).where(Project.id.not_in(archived_ids))

    # Sorting — column allowlist so users can't reach into class internals.
    if sort_by not in _SORTABLE_COLUMNS:
        sort_by = "total_lines"
    sort_column = getattr(Project, sort_by)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Pagination
    query = query.offset(offset).limit(limit)

    projects = session.exec(query).all()
    return [get_project_response(p, session) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int, session: Session = Depends(get_session)):
    """Get a single project."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return get_project_response(project, session)


@router.patch("/{project_id}/flags", response_model=ProjectResponse)
async def update_project_flags(
    project_id: int,
    request: ProjectFlagUpdate,
    session: Session = Depends(get_session),
):
    """Update project flags (replaces all existing flags)."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Validate flag types
    for flag_type in request.flags:
        if flag_type not in FLAG_TYPES:
            raise HTTPException(
                status_code=400, detail=f"Invalid flag type: {flag_type}. Valid types: {FLAG_TYPES}"
            )

    # Remove existing flags
    existing_flags = session.exec(
        select(ProjectFlag).where(ProjectFlag.project_id == project_id)
    ).all()
    for flag in existing_flags:
        session.delete(flag)

    # Add new flags
    for flag_type in request.flags:
        flag = ProjectFlag(project_id=project_id, flag_type=flag_type)
        session.add(flag)

    session.commit()
    session.refresh(project)

    return get_project_response(project, session)


@router.post("/{project_id}/tags/{tag_id}", response_model=ProjectResponse)
async def add_tag_to_project(
    project_id: int,
    tag_id: int,
    session: Session = Depends(get_session),
):
    """Add a tag to a project."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    tag = session.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    # Check if already exists
    existing = session.exec(
        select(ProjectTag)
        .where(ProjectTag.project_id == project_id)
        .where(ProjectTag.tag_id == tag_id)
    ).first()

    if not existing:
        project_tag = ProjectTag(project_id=project_id, tag_id=tag_id)
        session.add(project_tag)
        session.commit()

    session.refresh(project)
    return get_project_response(project, session)


@router.delete("/{project_id}/tags/{tag_id}", response_model=ProjectResponse)
async def remove_tag_from_project(
    project_id: int,
    tag_id: int,
    session: Session = Depends(get_session),
):
    """Remove a tag from a project."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project_tag = session.exec(
        select(ProjectTag)
        .where(ProjectTag.project_id == project_id)
        .where(ProjectTag.tag_id == tag_id)
    ).first()

    if project_tag:
        session.delete(project_tag)
        session.commit()

    session.refresh(project)
    return get_project_response(project, session)


@router.post("/{project_id}/refresh", response_model=ProjectResponse)
async def refresh_project_analysis(
    project_id: int,
    session: Session = Depends(get_session),
):
    """Re-analyze a project and update its metrics."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Path-jail check on the DB-stored project path.
    from web.backend.security.path_jail import PathJailError, resolve_and_check

    try:
        resolve_and_check(project.path)
    except PathJailError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    # Verify path still exists
    project_path = Path(project.path)
    if not project_path.exists():
        raise HTTPException(status_code=400, detail="Project path no longer exists")

    # Re-analyze the project
    try:
        analyzer_service = AnalyzerService()
        # Import analyze_project from batch_analyze
        import sys
        from pathlib import Path as P

        PROJECT_ROOT = P(__file__).parents[3]
        sys.path.insert(0, str(PROJECT_ROOT))
        from batch_analyze import analyze_project

        summary = analyze_project(project_path, analyzer_service.analyzer)

        if not summary or summary.total_files == 0:
            raise HTTPException(status_code=400, detail="Failed to analyze project")

        # Update project with new analysis results
        result = asdict(summary)
        project.name = result.get("name", project.name)
        project.total_dirs = result.get("total_dirs", 0)
        project.total_files = result.get("total_files", 0)
        project.total_lines = result.get("total_lines", 0)
        project.code_lines = result.get("code_lines", 0)
        project.comment_lines = result.get("comment_lines", 0)
        project.blank_lines = result.get("blank_lines", 0)
        project.characters = result.get("characters", 0)
        project.words = result.get("words", 0)
        project.functions = result.get("functions", 0)
        project.classes = result.get("classes", 0)
        project.todos = result.get("todos", 0)
        project.imports = result.get("imports", 0)
        project.languages = result.get("languages", [])
        project.avg_lines_per_file = result.get("avg_lines_per_file", 0.0)
        project.test_files = result.get("test_files", 0)
        project.test_total_lines = result.get("test_total_lines", 0)
        project.test_code_lines = result.get("test_code_lines", 0)
        project.todo_items = result.get("todo_items") or []
        project.dependencies = result.get("dependencies") or []
        project.complex_functions = result.get("complex_functions") or []
        project.jsx_components = result.get("jsx_components", 0)
        project.react_hooks = result.get("react_hooks", 0)
        project.async_functions = result.get("async_functions", 0)
        project.interfaces = result.get("interfaces", 0)
        project.type_aliases = result.get("type_aliases", 0)
        project.enums = result.get("enums", 0)
        project.repo_url = result.get("repo_url")
        raw_commit_at = result.get("last_commit_at")
        if raw_commit_at:
            try:
                project.last_commit_at = datetime.fromisoformat(
                    raw_commit_at.replace("Z", "+00:00")
                )
            except ValueError:
                project.last_commit_at = None
        else:
            project.last_commit_at = None

        session.add(project)
        session.commit()
        session.refresh(project)

        return get_project_response(project, session)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to re-analyze project: {str(e)}"
        ) from e


# Top-N dashboard panels -------------------------------------------------------


def _to_highlight(project: Project) -> ProjectHighlight:
    return ProjectHighlight(
        id=project.id,
        analysis_id=project.analysis_id,
        name=project.name,
        path=project.path,
        total_lines=project.total_lines,
        total_files=project.total_files,
        todos=project.todos,
        last_commit_at=project.last_commit_at,
        health_score=compute_health(project).score,
    )


@router.get("/compare/", response_model=ProjectCompareResponse)
async def compare_projects(
    ids: str = Query(..., description="Comma-separated project IDs to compare (max 8)"),
    session: Session = Depends(get_session),
):
    """Return side-by-side snapshots for N projects. Capped at 8 to keep the
    UI sensible — the side-by-side table layout starts to break beyond that."""
    raw_ids = [s.strip() for s in ids.split(",") if s.strip()]
    if not raw_ids:
        raise HTTPException(status_code=400, detail="ids cannot be empty")
    if len(raw_ids) > 8:
        raise HTTPException(status_code=400, detail="cannot compare more than 8 projects at once")

    try:
        project_ids = [int(s) for s in raw_ids]
    except ValueError as err:
        raise HTTPException(status_code=400, detail="ids must be comma-separated integers") from err

    entries: list[ProjectCompareEntry] = []
    for project_id in project_ids:
        project = session.get(Project, project_id)
        if project is None:
            # Surface clearly which id failed rather than returning a partial response.
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        analysis = session.get(Analysis, project.analysis_id)
        if analysis is None:
            raise HTTPException(
                status_code=500, detail=f"Analysis for project {project_id} missing"
            )
        entries.append(
            ProjectCompareEntry(
                id=project.id,
                name=project.name,
                path=project.path,
                analysis_id=project.analysis_id,
                analyzed_at=analysis.analyzed_at,
                total_files=project.total_files,
                total_lines=project.total_lines,
                code_lines=project.code_lines,
                comment_lines=project.comment_lines,
                blank_lines=project.blank_lines,
                functions=project.functions,
                classes=project.classes,
                todos=project.todos,
                imports=project.imports,
                test_files=project.test_files,
                test_total_lines=project.test_total_lines,
                avg_lines_per_file=project.avg_lines_per_file,
                languages=list(project.languages or []),
                last_commit_at=project.last_commit_at,
                health_score=compute_health(project).score,
            )
        )

    return ProjectCompareResponse(projects=entries)


@router.get("/dependencies/", response_model=DependencyUsageResponse)
async def dependency_usage(
    min_projects: int = Query(1, ge=1, le=100),
    session: Session = Depends(get_session),
):
    """Group every declared dependency by package manager + name, listing
    which projects use each one. Latest analysis per project path wins."""
    rows = session.exec(
        select(Project, Analysis.analyzed_at)
        .join(Analysis, Analysis.id == Project.analysis_id)
        .where(Analysis.status == "completed")
        .order_by(Analysis.analyzed_at.desc())
    ).all()

    latest: dict[str, Project] = {}
    for row in rows:
        project = row[0] if isinstance(row, tuple) else row
        latest.setdefault(project.path, project)

    # Bucket: (manager, name) -> list of {id, name, version}
    grouped: dict[tuple[str, str], list[dict]] = {}
    for project in latest.values():
        deps = project.dependencies or []
        for dep in deps:
            name = dep.get("name")
            manager = dep.get("manager")
            if not isinstance(name, str) or not isinstance(manager, str):
                continue
            key = (manager, name)
            grouped.setdefault(key, []).append(
                {
                    "id": project.id,
                    "name": project.name,
                    "version": dep.get("version"),
                }
            )

    by_manager: dict[str, list[DependencyUsage]] = {}
    total_unique = 0
    for (manager, name), projects in grouped.items():
        if len(projects) < min_projects:
            continue
        total_unique += 1
        by_manager.setdefault(manager, []).append(
            DependencyUsage(
                name=name,
                manager=manager,
                project_count=len(projects),
                projects=projects,
            )
        )

    # Sort each manager's list by usage descending, then alphabetically.
    for mgr in by_manager:
        by_manager[mgr].sort(key=lambda d: (-d.project_count, d.name.lower()))

    return DependencyUsageResponse(by_manager=by_manager, total_unique=total_unique)


_VALID_FLAG_OPERATIONS = {"add", "remove", "replace"}
_VALID_TAG_OPERATIONS = {"add", "remove"}
_BULK_PROJECT_LIMIT = 500  # belt-and-braces cap so a typo doesn't melt the DB


@router.post("/bulk/flags", response_model=BulkResult)
async def bulk_update_flags(request: BulkFlagRequest, session: Session = Depends(get_session)):
    """Add / remove / replace flags across many projects in one call."""
    if request.operation not in _VALID_FLAG_OPERATIONS:
        raise HTTPException(
            status_code=400, detail=f"operation must be one of {sorted(_VALID_FLAG_OPERATIONS)}"
        )
    for flag_type in request.flags:
        if flag_type not in FLAG_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid flag type: {flag_type}")
    if not request.project_ids:
        return BulkResult(updated=0, skipped=0, project_ids=[])
    if len(request.project_ids) > _BULK_PROJECT_LIMIT:
        raise HTTPException(
            status_code=400, detail=f"too many project_ids (max {_BULK_PROJECT_LIMIT})"
        )

    updated_ids: list[int] = []
    skipped = 0
    for project_id in request.project_ids:
        project = session.get(Project, project_id)
        if project is None:
            skipped += 1
            continue

        existing = {f.flag_type for f in project.flags}
        if request.operation == "replace":
            target = set(request.flags)
        elif request.operation == "add":
            target = existing | set(request.flags)
        else:  # remove
            target = existing - set(request.flags)

        if target == existing:
            updated_ids.append(project_id)
            continue

        # Sync to target set.
        for flag in list(project.flags):
            if flag.flag_type not in target:
                session.delete(flag)
        for flag_type in target - existing:
            session.add(ProjectFlag(project_id=project_id, flag_type=flag_type))
        updated_ids.append(project_id)

    session.commit()
    return BulkResult(updated=len(updated_ids), skipped=skipped, project_ids=updated_ids)


@router.post("/bulk/tags", response_model=BulkResult)
async def bulk_update_tag(request: BulkTagRequest, session: Session = Depends(get_session)):
    """Add or remove a single tag across many projects."""
    if request.operation not in _VALID_TAG_OPERATIONS:
        raise HTTPException(
            status_code=400, detail=f"operation must be one of {sorted(_VALID_TAG_OPERATIONS)}"
        )
    if not request.project_ids:
        return BulkResult(updated=0, skipped=0, project_ids=[])
    if len(request.project_ids) > _BULK_PROJECT_LIMIT:
        raise HTTPException(
            status_code=400, detail=f"too many project_ids (max {_BULK_PROJECT_LIMIT})"
        )

    tag = session.get(Tag, request.tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")

    updated_ids: list[int] = []
    skipped = 0
    for project_id in request.project_ids:
        project = session.get(Project, project_id)
        if project is None:
            skipped += 1
            continue

        existing = session.exec(
            select(ProjectTag)
            .where(ProjectTag.project_id == project_id)
            .where(ProjectTag.tag_id == request.tag_id)
        ).first()

        if request.operation == "add" and existing is None:
            session.add(ProjectTag(project_id=project_id, tag_id=request.tag_id))
        elif request.operation == "remove" and existing is not None:
            session.delete(existing)
        # else: idempotent — nothing to do, still count as "updated" (successfully reached target state).
        updated_ids.append(project_id)

    session.commit()
    return BulkResult(updated=len(updated_ids), skipped=skipped, project_ids=updated_ids)


@router.get("/highlights/", response_model=ProjectHighlightsResponse)
async def project_highlights(
    limit: int = Query(5, ge=1, le=25),
    session: Session = Depends(get_session),
):
    """Aggregate panel data: only the most recent Project row per path counts.

    Cheap because the underlying tables are small (one row per (analysis, project))
    and the dedup is done in Python — clearer than the equivalent SQL window
    function across SQLite + portable Postgres.
    """
    # Pull all completed projects newest-analysis first; keep the first row per path.
    rows = session.exec(
        select(Project, Analysis.analyzed_at)
        .join(Analysis, Analysis.id == Project.analysis_id)
        .where(Analysis.status == "completed")
        .order_by(Analysis.analyzed_at.desc())
    ).all()

    latest: dict[str, Project] = {}
    for row in rows:
        # `session.exec` returns a Project when the select has one entity, and
        # a Row tuple when there are extras. Cope with both.
        project = row[0] if isinstance(row, tuple) else row
        if project.path in latest:
            continue
        latest[project.path] = project

    projects = list(latest.values())

    def top(key, *, reverse: bool = True, fallback_filter=None) -> list[Project]:
        items = [p for p in projects if (fallback_filter(p) if fallback_filter else True)]
        items.sort(key=key, reverse=reverse)
        return items[:limit]

    # For staleness, treat "never committed" as infinitely stale by using
    # datetime.min as the sort key. Skip archived flag, since those are
    # intentionally inactive.
    from datetime import datetime as _dt

    EPOCH = _dt(1970, 1, 1, tzinfo=timezone.utc)

    def commit_age_key(p: Project):
        last = p.last_commit_at
        if last is None:
            return EPOCH
        return last.replace(tzinfo=timezone.utc) if last.tzinfo is None else last

    archived_paths = {
        pf.project.path
        for pf in session.exec(select(ProjectFlag).where(ProjectFlag.flag_type == "archived")).all()
        if pf.project is not None
    }

    biggest = top(lambda p: p.total_lines)
    stalest_pool = [p for p in projects if p.path not in archived_paths]
    stalest_pool.sort(key=commit_age_key)
    stalest = stalest_pool[:limit]
    todo_heavy = top(lambda p: p.todos)
    todo_heavy = [p for p in todo_heavy if p.todos > 0]  # don't show "0 TODOs" rows
    lowest_health_pool = sorted(projects, key=lambda p: compute_health(p).score)
    lowest_health = lowest_health_pool[:limit]

    return ProjectHighlightsResponse(
        biggest=[_to_highlight(p) for p in biggest],
        stalest=[_to_highlight(p) for p in stalest],
        todo_heavy=[_to_highlight(p) for p in todo_heavy],
        lowest_health=[_to_highlight(p) for p in lowest_health],
    )


# Diff mode --------------------------------------------------------------------

_DIFF_METRICS = (
    "total_files",
    "total_lines",
    "code_lines",
    "comment_lines",
    "blank_lines",
    "functions",
    "classes",
    "todos",
    "imports",
    "test_files",
    "test_total_lines",
    "test_code_lines",
)


def _snapshot(project: Project, analysis: Analysis) -> ProjectMetricsSnapshot:
    return ProjectMetricsSnapshot(
        analysis_id=project.analysis_id,
        project_id=project.id,
        analyzed_at=analysis.analyzed_at,
        total_files=project.total_files,
        total_lines=project.total_lines,
        code_lines=project.code_lines,
        comment_lines=project.comment_lines,
        blank_lines=project.blank_lines,
        functions=project.functions,
        classes=project.classes,
        todos=project.todos,
        imports=project.imports,
        test_files=project.test_files,
        test_total_lines=project.test_total_lines,
        test_code_lines=project.test_code_lines,
        languages=list(project.languages or []),
        health_score=compute_health(project).score,
    )


def _build_diff(
    before: ProjectMetricsSnapshot, after: ProjectMetricsSnapshot
) -> list[ProjectDiffEntry]:
    entries: list[ProjectDiffEntry] = []
    for metric in _DIFF_METRICS:
        b = float(getattr(before, metric))
        a = float(getattr(after, metric))
        delta_pct = ((a - b) / b * 100) if b > 0 else None
        entries.append(
            ProjectDiffEntry(metric=metric, before=b, after=a, delta=a - b, delta_pct=delta_pct)
        )
    # Health score is special — it's already a derived 0-100 value.
    entries.append(
        ProjectDiffEntry(
            metric="health_score",
            before=float(before.health_score),
            after=float(after.health_score),
            delta=float(after.health_score) - float(before.health_score),
            delta_pct=None,
        )
    )
    return entries


@router.get("/{project_id}/diff", response_model=ProjectDiffResponse)
async def diff_project(
    project_id: int,
    other: int | None = Query(
        None,
        description="Other project ID to diff against (defaults to previous analysis of same path)",
    ),
    session: Session = Depends(get_session),
):
    """Diff two analyses of the same project path. By default, diffs the
    given project against the most recent earlier analysis of the same path."""
    after_project = session.get(Project, project_id)
    if not after_project:
        raise HTTPException(status_code=404, detail="Project not found")
    after_analysis = session.get(Analysis, after_project.analysis_id)
    if not after_analysis:
        raise HTTPException(status_code=404, detail="Analysis not found for project")

    if other is not None:
        before_project = session.get(Project, other)
        if not before_project:
            raise HTTPException(status_code=404, detail="Other project not found")
        if before_project.path != after_project.path:
            raise HTTPException(status_code=400, detail="Projects don't share a path; can't diff")
    else:
        # Pick the most recent earlier analysis of the same path.
        before_project = session.exec(
            select(Project)
            .join(Analysis, Analysis.id == Project.analysis_id)
            .where(Project.path == after_project.path)
            .where(Project.id != after_project.id)
            .where(Analysis.analyzed_at < after_analysis.analyzed_at)
            .order_by(Analysis.analyzed_at.desc())
            .limit(1)
        ).first()
        if before_project is None:
            raise HTTPException(status_code=404, detail="No earlier analysis to diff against")

    before_analysis = session.get(Analysis, before_project.analysis_id)

    # Ensure chronological order: if user passed `other` for a newer analysis,
    # swap so "before" really is before.
    if before_analysis and before_analysis.analyzed_at > after_analysis.analyzed_at:
        before_project, after_project = after_project, before_project
        before_analysis, after_analysis = after_analysis, before_analysis

    before_snap = _snapshot(before_project, before_analysis)
    after_snap = _snapshot(after_project, after_analysis)

    before_langs = set(before_snap.languages or [])
    after_langs = set(after_snap.languages or [])

    return ProjectDiffResponse(
        project_path=after_project.path,
        before=before_snap,
        after=after_snap,
        entries=_build_diff(before_snap, after_snap),
        days_between=(after_analysis.analyzed_at - before_analysis.analyzed_at).total_seconds()
        / 86400.0,
        languages_added=sorted(after_langs - before_langs),
        languages_removed=sorted(before_langs - after_langs),
    )


@router.get("/{project_id}/health", response_model=HealthResponse)
async def get_project_health(project_id: int, session: Session = Depends(get_session)):
    """Return the project's health score with its component breakdown."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    breakdown = compute_health(project)
    return HealthResponse(
        project_id=project_id,
        score=breakdown.score,
        components=[
            HealthComponentResponse(name=c.name, score=c.score, weight=c.weight, detail=c.detail)
            for c in breakdown.components
        ],
    )


@router.get("/{project_id}/notes", response_model=dict)
async def get_project_notes(project_id: int, session: Session = Depends(get_session)):
    """Get the free-text notes attached to this project's directory."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return {"path": project.path, "notes": _get_note_text(session, project.path)}


@router.put("/{project_id}/notes", response_model=dict)
async def update_project_notes(
    project_id: int,
    payload: ProjectNoteUpdate,
    session: Session = Depends(get_session),
):
    """Replace this project's notes. Notes are keyed by path so they persist
    across re-analyses."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Light hygiene — clamp ridiculously large payloads, strip BOM/null bytes.
    text = (payload.notes or "")[:100_000].replace("\x00", "")

    note = session.get(ProjectNote, project.path)
    if note is None:
        note = ProjectNote(path=project.path, notes=text, updated_at=datetime.now(timezone.utc))
        session.add(note)
    else:
        note.notes = text
        note.updated_at = datetime.now(timezone.utc)
    session.commit()

    return {"path": project.path, "notes": note.notes}

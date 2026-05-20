"""Analysis API routes."""

import asyncio
import logging
import threading
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from sqlmodel import Session, select

from ..database.connection import engine, get_session
from ..database.models import Analysis, Project, RecentPath
from ..schemas.analysis import (
    AnalysisCreate,
    AnalysisListResponse,
    AnalysisResponse,
    AnalysisStatus,
)
from ..services.analyzer_service import AnalyzerService, validate_directory
from .routes_projects import get_project_response

logger = logging.getLogger(__name__)
router = APIRouter()

# Active WebSocket connections by analysis ID. Mutated from the asyncio loop
# (websocket handler) and read from broadcast_progress on the same loop, so a
# simple dict + per-call snapshot is enough — but we still take a lock on writes
# to be safe against future code that might mutate this from threads.
active_connections: dict[int, list[WebSocket]] = {}
_connections_lock = threading.Lock()

# Loop captured by main.py lifespan startup so background-thread analysis tasks
# can schedule broadcasts back into the event loop.
main_loop: asyncio.AbstractEventLoop | None = None


async def broadcast_progress(analysis_id: int, data: dict):
    """Send progress update to all connected WebSocket clients."""
    sockets = list(active_connections.get(analysis_id, ()))
    if not sockets:
        return
    disconnected = []
    for ws in sockets:
        try:
            await ws.send_json(data)
        except Exception:
            disconnected.append(ws)
    if disconnected:
        with _connections_lock:
            current = active_connections.get(analysis_id, [])
            for ws in disconnected:
                if ws in current:
                    current.remove(ws)
            if not current:
                active_connections.pop(analysis_id, None)


def _parse_iso(raw: str | None) -> datetime | None:
    """Parse the ISO-8601 string returned by `git log %aI` into a datetime."""
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def schedule_broadcast(analysis_id: int, data: dict):
    """Schedule a broadcast in the main event loop from a background thread."""
    if main_loop is None or not main_loop.is_running():
        logger.debug("dropped broadcast for analysis %s: loop unavailable", analysis_id)
        return
    asyncio.run_coroutine_threadsafe(
        broadcast_progress(analysis_id, data),
        main_loop,
    )


def run_analysis_sync(analysis_id: int, directory: str, filters: dict):
    """Synchronous analysis task (runs in background)."""
    # Create a new session for this background task
    with Session(engine) as session:
        try:
            # Update status to running
            analysis = session.get(Analysis, analysis_id)
            if not analysis:
                return
            analysis.status = "running"
            session.commit()

            # Send initial progress
            schedule_broadcast(
                analysis_id,
                {
                    "status": "running",
                    "current": 0,
                    "total": 0,
                    "project_name": "",
                    "message": "Discovering projects...",
                    "logs": [],
                },
            )

            # Create analyzer service
            service = AnalyzerService()

            # Discover projects
            project_dirs = service.discover_projects(
                directory,
                github_user=filters.get("github_user"),
                skip_public_sdks=filters.get("skip_public_sdks", True),
                include_internal=filters.get("include_internal", False),
            )

            total_projects = len(project_dirs)

            # Send discovery complete message
            schedule_broadcast(
                analysis_id,
                {
                    "status": "running",
                    "current": 0,
                    "total": total_projects,
                    "project_name": "",
                    "message": f"Found {total_projects} projects. Starting analysis...",
                    "logs": [f"Discovered {total_projects} projects in {directory}"],
                },
            )

            # Define progress callback
            def progress_callback(current: int, total: int, project_name: str):
                schedule_broadcast(
                    analysis_id,
                    {
                        "status": "running",
                        "current": current,
                        "total": total,
                        "project_name": project_name,
                        "message": f"Analyzing project {current}/{total}: {project_name}",
                        "logs": [f"[{current}/{total}] Analyzing: {project_name}"],
                    },
                )

            # Analyze projects
            results = service.analyze_projects(
                project_dirs,
                max_files=filters.get("max_files", 0),
                progress_callback=progress_callback,
            )

            # Save results to database
            total_files = 0
            total_lines = 0
            total_code_lines = 0
            total_functions = 0
            total_classes = 0

            for result in results:
                project = Project(
                    analysis_id=analysis_id,
                    name=result["name"],
                    path=result["path"],
                    total_dirs=result["total_dirs"],
                    total_files=result["total_files"],
                    total_lines=result["total_lines"],
                    code_lines=result["code_lines"],
                    comment_lines=result["comment_lines"],
                    blank_lines=result["blank_lines"],
                    characters=result["characters"],
                    words=result["words"],
                    functions=result["functions"],
                    classes=result["classes"],
                    todos=result["todos"],
                    imports=result["imports"],
                    languages=result["languages"],
                    avg_lines_per_file=result["avg_lines_per_file"],
                    test_files=result.get("test_files", 0),
                    test_total_lines=result.get("test_total_lines", 0),
                    test_code_lines=result.get("test_code_lines", 0),
                    repo_url=result.get("repo_url"),
                    last_commit_at=_parse_iso(result.get("last_commit_at")),
                    todo_items=result.get("todo_items") or [],
                    dependencies=result.get("dependencies") or [],
                    complex_functions=result.get("complex_functions") or [],
                    jsx_components=result.get("jsx_components", 0),
                    react_hooks=result.get("react_hooks", 0),
                    async_functions=result.get("async_functions", 0),
                    interfaces=result.get("interfaces", 0),
                    type_aliases=result.get("type_aliases", 0),
                    enums=result.get("enums", 0),
                    secrets_found=result.get("secrets_found", 0),
                    secrets_detail=result.get("secrets_detail"),
                    license_spdx=result.get("license_spdx"),
                )
                session.add(project)

                total_files += result["total_files"]
                total_lines += result["total_lines"]
                total_code_lines += result["code_lines"]
                total_functions += result["functions"]
                total_classes += result["classes"]

            # Update analysis totals
            analysis.completed_at = datetime.utcnow()
            analysis.status = "completed"
            analysis.total_projects = len(results)
            analysis.total_files = total_files
            analysis.total_lines = total_lines
            analysis.total_code_lines = total_code_lines
            analysis.total_functions = total_functions
            analysis.total_classes = total_classes
            session.commit()

            # Send completion message
            schedule_broadcast(
                analysis_id,
                {
                    "status": "completed",
                    "current": total_projects,
                    "total": total_projects,
                    "project_name": "",
                    "message": f"Analysis complete! Analyzed {len(results)} projects.",
                    "logs": [
                        "Analysis completed successfully",
                        f"Total projects: {len(results)}",
                        f"Total files: {total_files:,}",
                        f"Total lines: {total_lines:,}",
                    ],
                },
            )

        except Exception as exc:
            logger.exception("analysis %s failed", analysis_id)
            analysis = session.get(Analysis, analysis_id)
            generic_message = "Analysis failed (see server logs)"
            if analysis:
                analysis.completed_at = datetime.utcnow()
                analysis.status = "failed"
                # Store a short reason for the UI but keep full traceback in
                # the server log only.
                analysis.error_message = f"{type(exc).__name__}: {exc}"
                session.commit()

            schedule_broadcast(
                analysis_id,
                {
                    "status": "failed",
                    "current": 0,
                    "total": 0,
                    "project_name": "",
                    "message": generic_message,
                    "error": type(exc).__name__,
                    "logs": [generic_message],
                },
            )


@router.post("/start", response_model=dict)
async def start_analysis(
    request: AnalysisCreate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """Start a new analysis."""
    global main_loop
    if main_loop is None:
        # Fallback in case lifespan hasn't captured the loop yet (e.g. tests).
        main_loop = asyncio.get_running_loop()

    # Path-jail check (no-op when METTLE_SCAN_ROOTS unset).
    from web.backend.security.path_jail import PathJailError, resolve_and_check

    try:
        resolve_and_check(request.directory_path)
    except PathJailError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    # Validate directory
    validation = validate_directory(request.directory_path)
    if not validation["exists"] or not validation["is_directory"]:
        raise HTTPException(status_code=400, detail="Invalid directory path")

    # Get or set filters
    filters = (
        request.filters.model_dump()
        if request.filters
        else {
            "github_user": None,
            "skip_public_sdks": True,
            "max_files": 0,
            "include_internal": False,
        }
    )

    # Create analysis record
    analysis = Analysis(
        directory_path=validation["path"],
        filters_applied=filters,
        status="pending",
    )
    session.add(analysis)
    session.commit()
    session.refresh(analysis)

    # Update recent paths
    recent = session.exec(select(RecentPath).where(RecentPath.path == validation["path"])).first()
    if recent:
        recent.last_used = datetime.now(timezone.utc)
        recent.use_count += 1
    else:
        recent = RecentPath(path=validation["path"])
        session.add(recent)
    session.commit()

    # Start background analysis
    background_tasks.add_task(
        run_analysis_sync,
        analysis.id,
        validation["path"],
        filters,
    )

    return {"id": analysis.id, "status": "pending"}


@router.get("/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(analysis_id: int, session: Session = Depends(get_session)):
    """Get analysis details with projects."""
    analysis = session.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # Load projects with flags and tags
    projects = session.exec(select(Project).where(Project.analysis_id == analysis_id)).all()

    project_responses = [get_project_response(p, session) for p in projects]

    return AnalysisResponse(
        id=analysis.id,
        directory_path=analysis.directory_path,
        analyzed_at=analysis.analyzed_at,
        status=analysis.status,
        total_projects=analysis.total_projects,
        total_files=analysis.total_files,
        total_lines=analysis.total_lines,
        total_code_lines=analysis.total_code_lines,
        total_functions=analysis.total_functions,
        total_classes=analysis.total_classes,
        filters_applied=analysis.filters_applied,
        error_message=analysis.error_message,
        projects=project_responses,
    )


@router.get("/status/{analysis_id}", response_model=AnalysisStatus)
async def get_analysis_status(analysis_id: int, session: Session = Depends(get_session)):
    """Get analysis status."""
    analysis = session.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return AnalysisStatus(
        status=analysis.status,
        total=analysis.total_projects,
        message=analysis.error_message or "",
    )


@router.get("/", response_model=list[AnalysisListResponse])
async def list_analyses(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    """List all analyses."""
    analyses = session.exec(
        select(Analysis).order_by(Analysis.analyzed_at.desc()).offset(offset).limit(limit)
    ).all()

    return [
        AnalysisListResponse(
            id=a.id,
            directory_path=a.directory_path,
            analyzed_at=a.analyzed_at,
            status=a.status,
            total_projects=a.total_projects,
            total_files=a.total_files,
            total_lines=a.total_lines,
        )
        for a in analyses
    ]


@router.delete("/{analysis_id}")
async def delete_analysis(analysis_id: int, session: Session = Depends(get_session)):
    """Delete an analysis and its projects."""
    analysis = session.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    session.delete(analysis)
    session.commit()

    return {"message": "Analysis deleted", "success": True}


@router.websocket("/ws/{analysis_id}")
async def websocket_progress(websocket: WebSocket, analysis_id: int):
    """WebSocket endpoint for real-time progress updates."""
    from web.backend.security import settings
    from web.backend.security.auth import authorize_websocket

    subprotocol = await authorize_websocket(websocket)
    if settings.token() is not None and subprotocol is None:
        return  # close() already called inside authorize_websocket
    await websocket.accept(subprotocol=subprotocol)

    with _connections_lock:
        active_connections.setdefault(analysis_id, []).append(websocket)

    try:
        while True:
            # Keep the connection alive but ignore client payload content; the
            # old echo was an amplification vector for arbitrary-size messages.
            await websocket.receive_text()
            await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("websocket %s errored", analysis_id)
    finally:
        with _connections_lock:
            sockets = active_connections.get(analysis_id)
            if sockets is not None and websocket in sockets:
                sockets.remove(websocket)
            if sockets is not None and not sockets:
                active_connections.pop(analysis_id, None)

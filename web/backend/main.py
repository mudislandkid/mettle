"""FastAPI main application for Mettle Web."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import routes_analysis, routes_export, routes_git, routes_projects, routes_tags
from .database.connection import run_migrations
from .security import settings as security_settings

# Get frontend dist path
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Capture the running event loop so background-thread analysis tasks can
    # schedule websocket broadcasts back into it. Lazy capture on the first
    # request can race or pick the wrong loop under multi-worker uvicorn.
    routes_analysis.main_loop = asyncio.get_running_loop()
    run_migrations()
    yield


# Read the debug flag once at startup. Disabling docs at the constructor level
# means there's no auth-bypass surface to worry about — the routes simply don't exist.
_debug = security_settings.is_debug()

app = FastAPI(
    title="Mettle Web API",
    description="Triage dashboard for the AI-coding era",
    version="0.9.0",
    docs_url="/docs" if _debug else None,
    openapi_url="/openapi.json" if _debug else None,
    redoc_url=None,
    lifespan=lifespan,
)

# Security middleware order matters:
#   CORS first (handles preflight OPTIONS before any auth check)
#   TokenAuth second (rejects unauthenticated requests before they reach routes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=security_settings.cors_origins(),
    allow_credentials=security_settings.token() is not None,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

from .security.auth import TokenAuthMiddleware  # noqa: E402 — must come after app

app.add_middleware(TokenAuthMiddleware, token=security_settings.token())

from .security.startup import validate_or_die  # noqa: E402

validate_or_die()

# API routes
app.include_router(
    routes_analysis.router,
    prefix="/api/analysis",
    tags=["analysis"],
)
app.include_router(
    routes_projects.router,
    prefix="/api/projects",
    tags=["projects"],
)
app.include_router(
    routes_git.router,
    prefix="/api/projects",
    tags=["git"],
)
app.include_router(
    routes_tags.router,
    prefix="/api/tags",
    tags=["tags"],
)
app.include_router(
    routes_export.router,
    prefix="/api",
    tags=["export"],
)


# Serve Vue frontend in production (if dist exists)
@app.get("/")
async def serve_frontend():
    """Serve the Vue frontend."""
    index_path = FRONTEND_DIST / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Mettle Web API", "docs": "/docs"}


# Serve static files if frontend is built
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

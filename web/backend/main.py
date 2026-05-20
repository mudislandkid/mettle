"""FastAPI main application for Mettle Web."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .database.connection import run_migrations
from .api import routes_analysis, routes_projects, routes_tags, routes_export, routes_git
from .config import CORS_ORIGINS

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


app = FastAPI(
    title="Mettle Web API",
    description="Triage dashboard for the AI-coding era",
    version="0.9.0",
    lifespan=lifespan,
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

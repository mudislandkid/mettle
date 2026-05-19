"""Configuration settings for CodeCounter Web."""

from pathlib import Path

# Base paths
WEB_DIR = Path(__file__).parent.parent
PROJECT_ROOT = WEB_DIR.parent
DATABASE_PATH = WEB_DIR / "codecounter.db"

# Database URL
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# API settings
API_PREFIX = "/api"

# CORS settings (for development)
CORS_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:8000",  # FastAPI server
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8000",
]

# Analysis settings
DEFAULT_MAX_FILES = 10000
DEFAULT_SKIP_PUBLIC_SDKS = True

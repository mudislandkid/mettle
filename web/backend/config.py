"""Configuration settings for Mettle Web."""

from pathlib import Path

# Base paths
WEB_DIR = Path(__file__).parent.parent
PROJECT_ROOT = WEB_DIR.parent
DATABASE_PATH = WEB_DIR / "mettle.db"

# Database URL
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# API settings
API_PREFIX = "/api"

# Analysis settings
DEFAULT_MAX_FILES = 10000
DEFAULT_SKIP_PUBLIC_SDKS = True

"""Configuration settings for Mettle Web."""

import os
from pathlib import Path

# Base paths
WEB_DIR = Path(__file__).parent.parent
PROJECT_ROOT = WEB_DIR.parent
DATABASE_PATH = WEB_DIR / "mettle.db"

# Database URL — overridable via METTLE_DATABASE_URL so tests can point at a
# tmp SQLite file instead of polluting the dev database.
DATABASE_URL = os.environ.get("METTLE_DATABASE_URL", f"sqlite:///{DATABASE_PATH}")

# API settings
API_PREFIX = "/api"

# Analysis settings
DEFAULT_MAX_FILES = 10000
DEFAULT_SKIP_PUBLIC_SDKS = True

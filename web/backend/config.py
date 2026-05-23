"""Configuration settings for Mettle Web."""

import os
import sys
from pathlib import Path

# Base paths
WEB_DIR = Path(__file__).parent.parent
PROJECT_ROOT = WEB_DIR.parent


def _resolve_data_dir() -> Path:
    """Where mettle.db + bundled migrations live at runtime.

    Desktop sidecar sets METTLE_DATA_DIR to a writable user location
    (e.g. ~/Library/Application Support/Mettle); dev/test fall back to web/.
    """
    raw = os.environ.get("METTLE_DATA_DIR", "").strip()
    if raw:
        p = Path(raw).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p
    return WEB_DIR


DATA_DIR = _resolve_data_dir()
DATABASE_PATH = DATA_DIR / "mettle.db"

# Database URL — overridable via METTLE_DATABASE_URL so tests can point at a
# tmp SQLite file instead of polluting the dev database.
DATABASE_URL = os.environ.get("METTLE_DATABASE_URL", f"sqlite:///{DATABASE_PATH}")


def alembic_ini_path() -> Path:
    """Locate alembic.ini for the current runtime.

    Order: METTLE_ALEMBIC_INI env override → PyInstaller bundle (_MEIPASS) →
    repo root (dev). The frozen path is rooted at the temp extraction dir
    PyInstaller sets up for one-file builds.
    """
    raw = os.environ.get("METTLE_ALEMBIC_INI", "").strip()
    if raw:
        return Path(raw)
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / "alembic.ini"
    return PROJECT_ROOT / "alembic.ini"


# API settings
API_PREFIX = "/api"

# Analysis settings
DEFAULT_MAX_FILES = 10000
DEFAULT_SKIP_PUBLIC_SDKS = True

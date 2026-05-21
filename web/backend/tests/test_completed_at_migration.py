"""Tests for migration 0003 — completed_at on analyses."""

import sqlite3
from pathlib import Path


def _alembic_config(db_path: Path):
    from alembic.config import Config

    repo_root = Path(__file__).resolve().parents[3]
    cfg = Config(str(repo_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(repo_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return cfg


def test_completed_at_column_exists_after_upgrade(tmp_path):
    from alembic import command

    db_path = tmp_path / "test.db"
    cfg = _alembic_config(db_path)
    command.upgrade(cfg, "head")

    conn = sqlite3.connect(db_path)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(analyses)").fetchall()}
    assert "completed_at" in cols


def test_downgrade_drops_completed_at(tmp_path):
    from alembic import command

    db_path = tmp_path / "test.db"
    cfg = _alembic_config(db_path)
    command.upgrade(cfg, "head")
    # Downgrade to the revision before 0003 so completed_at is dropped.
    command.downgrade(cfg, "0002")

    conn = sqlite3.connect(db_path)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(analyses)").fetchall()}
    assert "completed_at" not in cols

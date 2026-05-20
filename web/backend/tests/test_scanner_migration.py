"""Tests for alembic migration 0002 — scanner_columns."""

import sqlite3
from pathlib import Path


def _alembic_config(db_path: Path):
    from alembic.config import Config

    repo_root = Path(__file__).resolve().parents[3]
    cfg = Config(str(repo_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(repo_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return cfg


def test_scanner_columns_exist_after_upgrade(tmp_path):
    """alembic upgrade head adds the three new columns to the projects table."""
    from alembic import command

    db_path = tmp_path / "test.db"
    cfg = _alembic_config(db_path)
    command.upgrade(cfg, "head")

    conn = sqlite3.connect(db_path)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(projects)").fetchall()}
    assert "secrets_found" in cols
    assert "secrets_detail" in cols
    assert "license_spdx" in cols

    # license_spdx is indexed
    indexes = conn.execute("PRAGMA index_list(projects)").fetchall()
    index_names = {row[1] for row in indexes}
    assert "ix_projects_license_spdx" in index_names


def test_downgrade_drops_columns(tmp_path):
    """alembic downgrade -1 removes the columns cleanly."""
    from alembic import command

    db_path = tmp_path / "test.db"
    cfg = _alembic_config(db_path)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0001")

    conn = sqlite3.connect(db_path)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(projects)").fetchall()}
    assert "secrets_found" not in cols
    assert "secrets_detail" not in cols
    assert "license_spdx" not in cols

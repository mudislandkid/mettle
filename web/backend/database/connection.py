"""Database connection and session management."""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import event
from sqlmodel import Session, create_engine

from alembic import command
from alembic.config import Config as AlembicConfig

from ..config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _enable_sqlite_pragmas(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def run_migrations() -> None:
    """Run Alembic migrations to head. Called at backend startup."""
    repo_root = Path(__file__).resolve().parents[3]
    alembic_cfg = AlembicConfig(str(repo_root / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    command.upgrade(alembic_cfg, "head")


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

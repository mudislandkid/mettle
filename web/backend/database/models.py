"""SQLModel database models for Mettle Web."""

from datetime import datetime

from sqlalchemy import ForeignKey, Index
from sqlmodel import JSON, Column, Field, Relationship, SQLModel


class Analysis(SQLModel, table=True):
    """Represents a batch analysis run."""

    __tablename__ = "analyses"

    id: int | None = Field(default=None, primary_key=True)
    directory_path: str = Field(index=True)
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    total_projects: int = Field(default=0)
    total_files: int = Field(default=0)
    total_lines: int = Field(default=0)
    total_code_lines: int = Field(default=0)
    total_functions: int = Field(default=0)
    total_classes: int = Field(default=0)
    filters_applied: dict | None = Field(default=None, sa_column=Column(JSON))
    status: str = Field(default="pending", index=True)  # pending, running, completed, failed
    error_message: str | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)

    # Relationships
    projects: list["Project"] = Relationship(
        back_populates="analysis",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class Project(SQLModel, table=True):
    """Individual project within an analysis."""

    __tablename__ = "projects"

    id: int | None = Field(default=None, primary_key=True)
    analysis_id: int = Field(
        sa_column=Column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True, nullable=False),
    )
    name: str = Field(index=True)
    path: str
    total_dirs: int = Field(default=0)
    total_files: int = Field(default=0)
    total_lines: int = Field(default=0)
    code_lines: int = Field(default=0)
    comment_lines: int = Field(default=0)
    blank_lines: int = Field(default=0)
    characters: int = Field(default=0)
    words: int = Field(default=0)
    functions: int = Field(default=0)
    classes: int = Field(default=0)
    todos: int = Field(default=0)
    imports: int = Field(default=0)
    languages: list | None = Field(default=None, sa_column=Column(JSON))
    avg_lines_per_file: float = Field(default=0)
    # Test-file segregation (heuristic: filename / parent-dir match)
    test_files: int = Field(default=0)
    test_total_lines: int = Field(default=0)
    test_code_lines: int = Field(default=0)
    # Git-derived metadata captured at analysis time. None when the directory
    # is not a git repo or `git remote` returned nothing.
    repo_url: str | None = Field(default=None)
    last_commit_at: datetime | None = Field(default=None, index=True)
    # Captured TODO/FIXME/XXX/HACK markers (file, line, marker, text). Stored
    # as a JSON list of dicts.
    todo_items: list | None = Field(default=None, sa_column=Column(JSON))
    # Declared dependencies pulled from package.json / pyproject.toml / etc.
    # JSON list of `{name, version, manager}` dicts.
    dependencies: list | None = Field(default=None, sa_column=Column(JSON))
    # Top-N most cyclomatically-complex functions (Python AST analyzer only).
    # JSON list of `{file, name, qualname, complexity, line}` dicts.
    complex_functions: list | None = Field(default=None, sa_column=Column(JSON))
    # JS/TS-specific aggregates. Zero for projects without those languages.
    jsx_components: int = Field(default=0)
    react_hooks: int = Field(default=0)
    async_functions: int = Field(default=0)
    interfaces: int = Field(default=0)
    type_aliases: int = Field(default=0)
    enums: int = Field(default=0)
    # Phase C — scanner output (0002_scanner_columns migration)
    secrets_found: int = Field(default=0)
    secrets_detail: list | None = Field(default=None, sa_column=Column(JSON))
    license_spdx: str | None = Field(default=None, index=True)

    # Relationships
    analysis: Analysis | None = Relationship(back_populates="projects")
    flags: list["ProjectFlag"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    project_tags: list["ProjectTag"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    @property
    def code_percentage(self) -> float:
        if self.total_lines == 0:
            return 0
        return (self.code_lines / self.total_lines) * 100

    @property
    def test_percentage(self) -> float:
        if self.total_lines == 0:
            return 0
        return (self.test_total_lines / self.total_lines) * 100


class ProjectFlag(SQLModel, table=True):
    """Flag assignment for a project."""

    __tablename__ = "project_flags"

    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(
        sa_column=Column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False),
    )
    flag_type: str = Field(
        index=True
    )  # not_mine, archived, wip, vendored, tutorial, fork, deprecated, production
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    project: Project | None = Relationship(back_populates="flags")

    class Config:
        # Unique constraint on project_id + flag_type
        table_args = (Index("idx_project_flag_unique", "project_id", "flag_type", unique=True),)


class Tag(SQLModel, table=True):
    """User-defined tag."""

    __tablename__ = "tags"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    color: str = Field(default="#6366f1")  # Indigo default
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    project_tags: list["ProjectTag"] = Relationship(
        back_populates="tag",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class ProjectTag(SQLModel, table=True):
    """Junction table for project-tag many-to-many relationship."""

    __tablename__ = "project_tags"

    project_id: int = Field(
        sa_column=Column(
            ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True, nullable=False
        ),
    )
    tag_id: int = Field(
        sa_column=Column(
            ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True, nullable=False
        ),
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    project: Project | None = Relationship(back_populates="project_tags")
    tag: Tag | None = Relationship(back_populates="project_tags")


class RecentPath(SQLModel, table=True):
    """Recently used directory paths for autocomplete."""

    __tablename__ = "recent_paths"

    id: int | None = Field(default=None, primary_key=True)
    path: str = Field(unique=True, index=True)
    last_used: datetime = Field(default_factory=datetime.utcnow)
    use_count: int = Field(default=1)


class ProjectNote(SQLModel, table=True):
    """Free-text notes attached to a project by its filesystem path.

    Keyed by `path` (not the surrogate Project.id) so notes survive
    re-analyses — every new analysis creates a fresh Project row, but the
    underlying directory is the stable identifier.
    """

    __tablename__ = "project_notes"

    path: str = Field(primary_key=True)
    notes: str = Field(default="")
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# Flag type constants
FLAG_TYPES = [
    "not_mine",
    "archived",
    "wip",
    "vendored",
    "tutorial",
    "fork",
    "deprecated",
    "production",
]

FLAG_LABELS = {
    "not_mine": "Not My Project",
    "archived": "Archived",
    "wip": "Work in Progress",
    "vendored": "Vendored/Third-party",
    "tutorial": "Tutorial/Learning",
    "fork": "Fork",
    "deprecated": "Deprecated",
    "production": "Production",
}

FLAG_COLORS = {
    "not_mine": "#6b7280",  # Gray
    "archived": "#eab308",  # Yellow
    "wip": "#3b82f6",  # Blue
    "vendored": "#a855f7",  # Purple
    "tutorial": "#22c55e",  # Green
    "fork": "#f97316",  # Orange
    "deprecated": "#ef4444",  # Red
    "production": "#10b981",  # Emerald
}

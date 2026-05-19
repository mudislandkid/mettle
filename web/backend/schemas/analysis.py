"""Pydantic schemas for analysis-related models."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AnalysisFilters(BaseModel):
    """Filters for project analysis."""
    github_user: Optional[str] = None
    skip_public_sdks: bool = True
    max_files: int = 0
    include_internal: bool = False


class AnalysisCreate(BaseModel):
    """Request to start a new analysis."""
    directory_path: str
    filters: Optional[AnalysisFilters] = None


class AnalysisStatus(BaseModel):
    """Status update for an analysis."""
    status: str  # pending, running, completed, failed
    current: int = 0
    total: int = 0
    project_name: str = ""
    message: str = ""
    error: Optional[str] = None


class FlagResponse(BaseModel):
    """Flag information for a project."""
    flag_type: str
    created_at: datetime

    class Config:
        from_attributes = True


class TagResponse(BaseModel):
    """Tag information."""
    id: int
    name: str
    color: str

    class Config:
        from_attributes = True


class ProjectResponse(BaseModel):
    """Response model for a project."""
    id: int
    analysis_id: int
    name: str
    path: str
    total_dirs: int
    total_files: int
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    characters: int
    words: int
    functions: int
    classes: int
    todos: int
    imports: int
    languages: Optional[list[str]] = None
    avg_lines_per_file: float
    code_percentage: float = 0
    test_files: int = 0
    test_total_lines: int = 0
    test_code_lines: int = 0
    test_percentage: float = 0
    repo_url: Optional[str] = None
    last_commit_at: Optional[datetime] = None
    health_score: float = 0
    todo_items: list[dict] = []
    dependencies: list[dict] = []
    complex_functions: list[dict] = []
    jsx_components: int = 0
    react_hooks: int = 0
    async_functions: int = 0
    interfaces: int = 0
    type_aliases: int = 0
    enums: int = 0
    notes: str = ""
    flags: list[str] = []
    tags: list[TagResponse] = []

    class Config:
        from_attributes = True


class ProjectNoteUpdate(BaseModel):
    """Body for PUT /projects/{id}/notes."""
    notes: str


class HealthComponentResponse(BaseModel):
    name: str
    score: float
    weight: float
    detail: str


class HealthResponse(BaseModel):
    project_id: int
    score: float
    components: list[HealthComponentResponse]


class ProjectHighlight(BaseModel):
    """Compact row used by the dashboard top-N panels."""
    id: int
    analysis_id: int
    name: str
    path: str
    total_lines: int
    total_files: int
    todos: int
    last_commit_at: Optional[datetime] = None
    health_score: float = 0


class ProjectHighlightsResponse(BaseModel):
    """Aggregates across all completed analyses, latest snapshot per path."""
    biggest: list[ProjectHighlight]
    stalest: list[ProjectHighlight]
    todo_heavy: list[ProjectHighlight]
    lowest_health: list[ProjectHighlight]


class DependencyUsage(BaseModel):
    """One row in the cross-project dependency view."""
    name: str
    manager: str
    project_count: int
    projects: list[dict]  # `{id, name, version}` for each project that declares it


class DependencyUsageResponse(BaseModel):
    """Cross-project dependency aggregation (latest analysis per project)."""
    by_manager: dict[str, list[DependencyUsage]]
    total_unique: int


class ProjectCompareEntry(BaseModel):
    """One project's snapshot in a comparison response."""
    id: int
    name: str
    path: str
    analysis_id: int
    analyzed_at: datetime
    total_files: int
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    functions: int
    classes: int
    todos: int
    imports: int
    test_files: int
    test_total_lines: int
    avg_lines_per_file: float
    languages: list[str]
    last_commit_at: Optional[datetime] = None
    health_score: float = 0


class ProjectCompareResponse(BaseModel):
    """Side-by-side comparison of N projects."""
    projects: list[ProjectCompareEntry]


class ProjectMetricsSnapshot(BaseModel):
    """The single-project metrics that participate in diff mode."""
    analysis_id: int
    project_id: int
    analyzed_at: datetime
    total_files: int
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    functions: int
    classes: int
    todos: int
    imports: int
    test_files: int
    test_total_lines: int
    test_code_lines: int
    languages: Optional[list[str]] = None
    health_score: float = 0


class ProjectDiffEntry(BaseModel):
    """One row in the diff table: a metric and its before/after/delta."""
    metric: str
    before: float
    after: float
    delta: float
    delta_pct: Optional[float] = None  # None when "before" was 0


class ProjectDiffResponse(BaseModel):
    """Diff between two analyses of the same project path."""
    project_path: str
    before: ProjectMetricsSnapshot
    after: ProjectMetricsSnapshot
    entries: list[ProjectDiffEntry]
    days_between: float
    languages_added: list[str] = []
    languages_removed: list[str] = []


class AnalysisResponse(BaseModel):
    """Response model for an analysis."""
    id: int
    directory_path: str
    analyzed_at: datetime
    status: str
    total_projects: int
    total_files: int
    total_lines: int
    total_code_lines: int
    total_functions: int
    total_classes: int
    filters_applied: Optional[dict] = None
    error_message: Optional[str] = None
    projects: list[ProjectResponse] = []

    class Config:
        from_attributes = True


class AnalysisListResponse(BaseModel):
    """Response model for listing analyses."""
    id: int
    directory_path: str
    analyzed_at: datetime
    status: str
    total_projects: int
    total_files: int
    total_lines: int

    class Config:
        from_attributes = True

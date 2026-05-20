"""Pydantic schemas for Git statistics API responses."""

from typing import Optional
from pydantic import BaseModel, Field


class GitCommitStats(BaseModel):
    """Statistics for commits on a specific date."""

    date: str = Field(..., description="Date in ISO format (YYYY-MM-DD)")
    commits_count: int = Field(..., description="Number of commits on this date")
    lines_added: int = Field(..., description="Total lines added on this date")
    lines_deleted: int = Field(..., description="Total lines deleted on this date")
    net_lines: int = Field(..., description="Net line change (added - deleted)")
    cumulative_lines: int = Field(..., description="Cumulative total lines in repo")
    authors: list[str] = Field(default_factory=list, description="Authors who committed on this date")

    class Config:
        json_schema_extra = {
            "example": {
                "date": "2024-01-15",
                "commits_count": 3,
                "lines_added": 245,
                "lines_deleted": 18,
                "net_lines": 227,
                "cumulative_lines": 15432,
                "authors": ["John Doe", "Jane Smith"]
            }
        }


class AuthorStats(BaseModel):
    """Per-author commit & churn totals."""

    author: str
    commits: int
    lines_added: int
    lines_deleted: int
    net_lines: int
    first_commit_date: str
    last_commit_date: str


class TimePatterns(BaseModel):
    """Commit time patterns by hour and day of week."""

    by_hour: list[int] = Field(
        default_factory=list,
        description="Commits by hour of day (0-23), list of 24 counts"
    )
    by_weekday: list[int] = Field(
        default_factory=list,
        description="Commits by day of week (0=Mon, 6=Sun), list of 7 counts"
    )
    heatmap: list[list[int]] = Field(
        default_factory=list,
        description="Heatmap data as [[weekday, hour, count], ...] for all 168 hour-day combinations"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "by_hour": [2, 1, 0, 0, 0, 0, 3, 8, 15, 22, 18, 12, 8, 10, 14, 20, 18, 12, 8, 5, 3, 4, 3, 2],
                "by_weekday": [25, 30, 28, 22, 20, 8, 5],
                "heatmap": [[0, 0, 2], [0, 1, 1], [0, 9, 5]]
            }
        }


class GitStatsResponse(BaseModel):
    """Complete Git statistics response for a project."""

    project_id: int = Field(..., description="Database ID of the project")
    project_name: str = Field(..., description="Name of the project")
    is_git_repo: bool = Field(..., description="Whether the project is a Git repository")
    total_commits: int = Field(default=0, description="Total number of commits")
    first_commit_date: Optional[str] = Field(None, description="Date of first commit (ISO format)")
    last_commit_date: Optional[str] = Field(None, description="Date of last commit (ISO format)")
    unique_authors: int = Field(default=0, description="Number of unique authors")
    commits: list[GitCommitStats] = Field(
        default_factory=list,
        description="Daily aggregated commit statistics"
    )
    monthly_commits: dict[str, int] = Field(
        default_factory=dict,
        description="Commits aggregated by month (YYYY-MM -> count)"
    )
    weekly_commits: dict[str, int] = Field(
        default_factory=dict,
        description="Commits aggregated by week (YYYY-Www -> count)"
    )
    heatmap_data: list[list] = Field(
        default_factory=list,
        description="Heatmap data as [[date, count], ...] pairs"
    )
    time_patterns: TimePatterns = Field(
        default_factory=TimePatterns,
        description="Commit patterns by hour and day of week"
    )
    authors: list[AuthorStats] = Field(
        default_factory=list,
        description="Top contributors ranked by commit count (up to 20)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": 1,
                "project_name": "Mettle",
                "is_git_repo": True,
                "total_commits": 127,
                "first_commit_date": "2023-06-15T10:30:00Z",
                "last_commit_date": "2024-12-29T14:22:00Z",
                "unique_authors": 3,
                "commits": [
                    {
                        "date": "2024-01-15",
                        "commits_count": 3,
                        "lines_added": 245,
                        "lines_deleted": 18,
                        "net_lines": 227,
                        "cumulative_lines": 15432,
                        "authors": ["John Doe"]
                    }
                ],
                "monthly_commits": {
                    "2024-01": 45,
                    "2024-02": 38
                },
                "weekly_commits": {
                    "2024-W01": 12,
                    "2024-W02": 15
                },
                "heatmap_data": [
                    ["2024-01-15", 3],
                    ["2024-01-16", 5]
                ]
            }
        }


class GitErrorResponse(BaseModel):
    """Error response for Git operations."""

    error: str = Field(..., description="Error message")
    is_git_repo: bool = Field(default=False, description="Whether the project is a Git repository")
    project_id: Optional[int] = Field(None, description="Project ID if available")
    project_name: Optional[str] = Field(None, description="Project name if available")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Not a Git repository",
                "is_git_repo": False,
                "project_id": 1,
                "project_name": "Mettle"
            }
        }

"""Pydantic mirrors of mettle.digest dataclasses for FastAPI response_model.

The dataclasses in mettle.digest are the source of truth; this file restates
them as Pydantic models so FastAPI can validate responses + emit OpenAPI.
"""

from datetime import datetime

from pydantic import BaseModel


class DigestEntryResponse(BaseModel):
    project_id: int
    project_name: str
    project_path: str
    repo_url: str | None = None
    headline_value: float
    headline_label: str
    baseline_value: float | None = None
    current_value: float | None = None
    extra: dict | None = None


class DigestSectionResponse(BaseModel):
    kind: str
    title: str
    description: str
    entries: list[DigestEntryResponse]
    empty_message: str | None = None


class DigestReportResponse(BaseModel):
    generated_at: datetime
    window_days: int
    window_start: datetime
    stale_days: int
    top_n: int
    total_projects: int
    projects_with_baseline: int
    projects_new: int
    projects_no_recent: int
    sections: list[DigestSectionResponse]

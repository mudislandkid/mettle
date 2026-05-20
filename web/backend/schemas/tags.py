"""Pydantic schemas for tag-related models."""

from datetime import datetime

from pydantic import BaseModel


class TagCreate(BaseModel):
    """Request to create a new tag."""

    name: str
    color: str = "#6366f1"


class TagUpdate(BaseModel):
    """Request to update a tag."""

    name: str | None = None
    color: str | None = None


class TagResponse(BaseModel):
    """Response model for a tag."""

    id: int
    name: str
    color: str
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectFlagUpdate(BaseModel):
    """Request to update project flags."""

    flags: list[str]  # List of flag_type strings


class BulkFlagRequest(BaseModel):
    """Bulk-edit flags for many projects at once.

    `operation` controls what `flags` does:
      - `replace` — replace each project's flags with this list verbatim
      - `add`     — union the listed flags with each project's existing flags
      - `remove`  — drop the listed flags from each project's existing flags
    """

    project_ids: list[int]
    flags: list[str]
    operation: str = "add"  # add | remove | replace


class BulkTagRequest(BaseModel):
    """Bulk add or remove a tag across many projects."""

    project_ids: list[int]
    tag_id: int
    operation: str = "add"  # add | remove


class BulkResult(BaseModel):
    """Generic result for bulk endpoints."""

    updated: int
    skipped: int
    project_ids: list[int]  # the ones that were successfully updated

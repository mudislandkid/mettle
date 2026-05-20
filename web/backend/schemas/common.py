"""Common Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel


class PathValidation(BaseModel):
    """Response for path validation."""

    exists: bool
    is_directory: bool
    path: str


class RecentPathResponse(BaseModel):
    """Response model for a recent path."""

    id: int
    path: str
    last_used: datetime
    use_count: int

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
    success: bool = True

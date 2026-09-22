from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class VideoCreate(BaseModel):
    title: str


class VideoResponse(BaseModel):
    id: UUID
    title: str
    source_type: str
    original_filename: str | None
    duration_seconds: float | None
    status: str
    created_at: datetime
    updated_at: datetime
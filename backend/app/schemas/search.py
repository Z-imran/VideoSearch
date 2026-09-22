from uuid import UUID
from pydantic import BaseModel


class SearchResult(BaseModel):
    id: UUID
    video_id: UUID
    video_title: str
    timestamp_seconds: float
    thumbnail_path: str
    similarity: float
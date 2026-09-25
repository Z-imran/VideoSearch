from uuid import UUID
from pydantic import BaseModel


class SearchResult(BaseModel):
    id: UUID
    video_id: UUID
    video_title: str
    timestamp_seconds: float
    matched_timestamp_seconds: float
    similarity: float
    thumbnail_url: str
    video_url: str

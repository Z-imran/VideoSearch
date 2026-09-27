from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql://videosearch:videosearch@localhost:5432/videosearch"
    storage_dir: str = "storage"
    storage_backend: Literal["local", "s3"] = "local"
    s3_bucket: str | None = None
    aws_region: str = "us-west-2"
    s3_presigned_url_seconds: int = Field(default=300, ge=60, le=3600)
    frontend_origin: str = "http://localhost:5173"
    max_query_image_bytes: int = 10 * 1024 * 1024
    max_search_results: int = 20
    uploads_enabled: bool = True
    max_video_bytes: int = 100 * 1024 * 1024
    max_video_duration_seconds: float = 180.0
    max_temporary_videos: int = 10
    temporary_video_ttl_hours: int = 24
    ffprobe_timeout_seconds: int = 15
    ffmpeg_timeout_seconds: int = 180
    frame_extract_timeout_seconds: int = 30
    cleanup_interval_seconds: int = 3600

    @model_validator(mode="after")
    def validate_storage_configuration(self):
        if self.storage_backend == "s3" and not self.s3_bucket:
            raise ValueError("S3_BUCKET is required when STORAGE_BACKEND=s3")
        return self

settings = Settings()

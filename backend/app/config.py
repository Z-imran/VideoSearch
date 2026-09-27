from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql://videosearch:videosearch@localhost:5432/videosearch"
    storage_dir: str = "storage"
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

settings = Settings()

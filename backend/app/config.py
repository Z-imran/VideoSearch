from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql://videosearch:videosearch@localhost:5432/videosearch"
    storage_dir: str = "storage"
    frontend_origin: str = "http://localhost:5173"
    max_query_image_bytes: int = 10 * 1024 * 1024
    max_search_results: int = 20

settings = Settings()

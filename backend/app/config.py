from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql://videosearch:videosearch@localhost:5432/videosearch"
    storage_dir: str = "storage"

settings = Settings()
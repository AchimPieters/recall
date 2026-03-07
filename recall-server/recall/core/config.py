from functools import lru_cache
from pydantic import BaseModel, Field
import os


class Settings(BaseModel):
    app_name: str = "Recall API"
    environment: str = Field(default_factory=lambda: os.getenv("RECALL_ENV", "dev"))
    database_url: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", "sqlite:///./recall.db"
        )
    )
    jwt_secret: str = Field(default_factory=lambda: os.getenv("JWT_SECRET", "change-me"))
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    media_dir: str = Field(default_factory=lambda: os.getenv("MEDIA_DIR", "/media"))
    max_upload_bytes: int = int(os.getenv("RECALL_MAX_UPLOAD_BYTES", str(200 * 1024 * 1024)))
    heartbeat_timeout_seconds: int = int(os.getenv("HEARTBEAT_TIMEOUT", "90"))


@lru_cache
def get_settings() -> Settings:
    return Settings()

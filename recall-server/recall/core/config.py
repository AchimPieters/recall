from functools import lru_cache
from pydantic import BaseModel, Field
import os


class Settings(BaseModel):
    app_name: str = "Recall API"
    environment: str = Field(default_factory=lambda: os.getenv("RECALL_ENV", "dev"))
    database_url: str = Field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./recall.db")
    )
    jwt_secret: str = Field(default_factory=lambda: os.getenv("JWT_SECRET", ""))
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_minutes: int = 60 * 24 * 14
    jwt_secrets: list[str] = Field(
        default_factory=lambda: [
            secret.strip()
            for secret in os.getenv("JWT_SECRETS", "").split(",")
            if secret.strip()
        ]
    )
    enforce_https: bool = Field(
        default_factory=lambda: os.getenv("RECALL_ENFORCE_HTTPS", "false").lower()
        == "true"
    )
    app_version: str = Field(
        default_factory=lambda: os.getenv("RECALL_VERSION", "0.2.0")
    )
    media_dir: str = Field(default_factory=lambda: os.getenv("MEDIA_DIR", "/media"))
    max_upload_bytes: int = int(
        os.getenv("RECALL_MAX_UPLOAD_BYTES", str(200 * 1024 * 1024))
    )
    heartbeat_timeout_seconds: int = int(os.getenv("HEARTBEAT_TIMEOUT", "90"))
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv(
                "RECALL_CORS_ORIGINS", "http://localhost,http://127.0.0.1"
            ).split(",")
            if origin.strip()
        ]
    )
    auto_create_schema: bool = Field(
        default_factory=lambda: os.getenv("RECALL_AUTO_CREATE_SCHEMA", "true").lower()
        == "true"
    )
    bootstrap_admin_username: str = Field(
        default_factory=lambda: os.getenv("RECALL_BOOTSTRAP_ADMIN_USERNAME", "admin")
    )
    bootstrap_admin_password: str = Field(
        default_factory=lambda: os.getenv("RECALL_BOOTSTRAP_ADMIN_PASSWORD", "")
    )
    redis_url: str = Field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0")
    )
    clamav_host: str = Field(
        default_factory=lambda: os.getenv("CLAMAV_HOST", "localhost")
    )
    clamav_port: int = int(os.getenv("CLAMAV_PORT", "3310"))
    clamav_fail_open: bool = Field(
        default_factory=lambda: os.getenv("RECALL_CLAMAV_FAIL_OPEN", "false").lower()
        == "true"
    )
    auth_lockout_threshold: int = Field(
        default_factory=lambda: int(os.getenv("RECALL_AUTH_LOCKOUT_THRESHOLD", "5")),
        ge=1,
    )
    auth_lockout_minutes: int = Field(
        default_factory=lambda: int(os.getenv("RECALL_AUTH_LOCKOUT_MINUTES", "15")),
        ge=1,
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.jwt_secrets:
        settings.jwt_secret = settings.jwt_secrets[0]

    if not settings.jwt_secret:
        if settings.environment == "dev":
            settings.jwt_secret = "dev-insecure-secret-change-me"
        else:
            raise ValueError("JWT_SECRET must be set outside development")
    if settings.environment != "dev" and settings.clamav_fail_open:
        raise ValueError("RECALL_CLAMAV_FAIL_OPEN must be false outside development")
    return settings

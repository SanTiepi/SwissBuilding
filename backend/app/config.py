"""
SwissBuildingOS - Application Configuration

Central configuration module using pydantic-settings.
All settings can be overridden via environment variables or .env file.
"""

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://swissbuildingos:swissbuildingos_dev_2024@postgres:5432/swissbuildingos"

    # JWT Authentication
    JWT_SECRET_KEY: str = ""  # Required — set via JWT_SECRET_KEY env var
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 480

    @model_validator(mode="after")
    def validate_jwt_secret(self):
        if not self.JWT_SECRET_KEY or self.JWT_SECRET_KEY == "":
            raise ValueError(
                "JWT_SECRET_KEY environment variable is required. "
                "Set a strong random secret (e.g. openssl rand -hex 32)"
            )
        return self

    # S3 / MinIO Object Storage
    S3_ENDPOINT: str = "http://minio:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "swissbuildingos-documents"

    # Redis (background jobs via Dramatiq)
    REDIS_URL: str = "redis://redis:6379/0"

    # Gotenberg (PDF generation)
    GOTENBERG_URL: str = "http://gotenberg:3000"

    # Meilisearch (full-text search)
    MEILISEARCH_HOST: str = "localhost"
    MEILISEARCH_PORT: int = 7700
    MEILISEARCH_MASTER_KEY: str = "swissbuildingos-dev-key"
    MEILISEARCH_ENABLED: bool = False  # disabled by default for tests

    # GlitchTip / Sentry (error monitoring)
    SENTRY_DSN: str = ""

    # Document processing — ClamAV (antivirus)
    CLAMAV_HOST: str = "clamav"
    CLAMAV_PORT: int = 3310
    CLAMAV_ENABLED: bool = True

    # Document processing — OCRmyPDF
    OCRMYPDF_ENABLED: bool = True
    OCRMYPDF_LANGUAGE: str = "fra+deu+ita+eng"  # Swiss multilingual

    # Batiscan Bridge (Consumer Bridge v1)
    BATISCAN_API_URL: str | None = None
    BATISCAN_API_KEY: str | None = None

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost",
    ]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


settings = Settings()

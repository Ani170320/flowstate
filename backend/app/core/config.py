import os
from typing import List, Optional
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables and .env file.
    Follows 12-factor app methodology using Pydantic Settings.
    """

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core Application Settings
    APP_NAME: str = "FLOWSTATE"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # Database Configuration (Supabase PostgreSQL)
    DATABASE_URL: Optional[str] = None
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_ECHO: bool = False

    # Frontend & CORS Configuration
    FRONTEND_URL: str = "http://localhost:3000"
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Security & Supabase Auth Configuration
    SECRET_KEY: str = "insecure-dev-secret-key-change-in-production"
    SUPABASE_URL: Optional[str] = None
    SUPABASE_JWT_SECRET: Optional[str] = None
    SUPABASE_JWT_ALGORITHM: str = "HS256"
    SUPABASE_JWT_AUDIENCE: Optional[str] = "authenticated"
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None

    # Supabase Storage Configuration
    STORAGE_BUCKET: str = "flowstate-attachments"
    STORAGE_MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB limit
    STORAGE_ALLOWED_MIME_TYPES: List[str] = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/svg+xml",
        "application/pdf",
        "text/plain",
        "text/csv",
        "text/markdown",
        "application/json",
        "application/zip",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ]

    @property
    def jwt_secret(self) -> str:
        """
        Returns the active secret used for JWT verification.
        Prefers SUPABASE_JWT_SECRET when provided; falls back to SECRET_KEY for dev/test.
        """
        if self.SUPABASE_JWT_SECRET and self.SUPABASE_JWT_SECRET.strip():
            return self.SUPABASE_JWT_SECRET.strip()
        return self.SECRET_KEY

    @computed_field
    @property
    def cors_origins(self) -> List[str]:
        """
        Derives all permitted CORS origins including FRONTEND_URL.
        """
        origins = list(self.ALLOWED_ORIGINS)
        if self.FRONTEND_URL and self.FRONTEND_URL not in origins:
            origins.append(self.FRONTEND_URL)
        return origins

    @property
    def is_production(self) -> bool:
        """Helper to check if running in production mode."""
        return self.APP_ENV.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Helper to check if running in development mode."""
        return self.APP_ENV.lower() == "development"

    @property
    def async_database_url(self) -> Optional[str]:
        """
        Normalizes standard PostgreSQL URLs for SQLAlchemy asyncpg.
        Converts 'postgres://' or 'postgresql://' to 'postgresql+asyncpg://'
        while preserving all query parameters and credentials safely.
        Returns None if placeholder password '[YOUR-PASSWORD]' is still present.
        """
        if not self.DATABASE_URL or not self.DATABASE_URL.strip():
            return None
        url = self.DATABASE_URL.strip()
        # If placeholder password is still present, treat as unconfigured
        if "[YOUR-PASSWORD]" in url or "[password]" in url.lower():
            return None
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        if url.startswith("postgresql://") and not url.startswith("postgresql+"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


# Singleton instance of settings
settings = Settings()

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR.parent / ".env"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Knowra"
    API_V1_STR: str = "/api/v1"

    # Security
    JWT_SECRET_KEY: str = "super-secret-key-change-in-prod-0123456789"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = "sqlite:///./knowra.db" # Using SQLite for standalone execution, switch to postgres URL for prod

    # LLM Settings (Phase 15 & 16)
    LLM_PROVIDER: str = "mock"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"

    # Embedding Settings (Phase 18)
    EMBEDDING_PROVIDER: str = "deterministic"
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSIONS: int = 384

    # SSO / OIDC Settings
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    MICROSOFT_TENANT_ID: str = "common"
    OAUTH_REDIRECT_BASE_URL: str = "http://localhost:8000/api/v1/auth"
    FRONTEND_URL: str = "http://localhost:3000"
    SSO_ENFORCE_BUSINESS_DOMAINS: bool = False
    RESTRICT_DOMAIN: str = "softude.com"  # Restrict registration, login, and SSO to this domain

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=ENV_FILE,
        extra="ignore",
    )


settings = Settings()
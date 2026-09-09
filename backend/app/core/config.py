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

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=ENV_FILE,
        extra="ignore",
    )


settings = Settings()
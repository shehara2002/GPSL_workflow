from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Greenpower SL Approvals Workflow"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "gpsl_workflow_super_secret_session_key_2026_change_in_prod"
    SESSION_COOKIE_NAME: str = "gpsl_session"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database Settings
    DATABASE_URL: str = "postgresql://postgres:2002@localhost:5432/GPSL_workflow_DB"

    # SMTP / Email Settings
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    # Password Reset Settings
    RESET_TOKEN_EXPIRE_MINUTES: int = 30
    APP_BASE_URL: str = "http://localhost:8000"

    @property
    def sqlalchemy_database_url(self) -> str:
        """
        Ensures the SQLAlchemy database URL uses the psycopg 3 driver scheme.
        Converts 'postgresql://' to 'postgresql+psycopg://'.
        """
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        elif url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
        return url

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

from pydantic_settings import BaseSettings
from functools import cached_property


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Telegram Bot
    BOT_TOKEN: str

    # Superadmin
    SUPERADMIN_TELEGRAM_ID: str
    
    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "helpdesk"
    POSTGRES_USER: str = "helpdesk_user"
    POSTGRES_PASSWORD: str = ""

    # FastAPI
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # AI Provider
    OPENROUTER_API_KEY: str = ""

    # Notion
    NOTION_TOKEN: str = ""
    NOTION_DATABASE_ID: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def superadmin_id(self) -> int | None:
        """Parse SUPERADMIN_TELEGRAM_ID as int. Returns None if not a numeric ID."""
        try:
            return int(self.SUPERADMIN_TELEGRAM_ID)
        except (ValueError, TypeError):
            return None

    @cached_property
    def DATABASE_URL(self) -> str:
        """Construct PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @cached_property
    def DATABASE_URL_SYNC(self) -> str:
        """Construct PostgreSQL connection URL for synchronous operations."""
        return (
            f"postgresql://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()

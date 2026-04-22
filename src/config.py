from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field, validator
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    BOT_TOKEN: str = Field(..., env="BOT_TOKEN")
    TELEGRAM_CHANNEL_ID: str = Field(..., env="TELEGRAM_CHANNEL_ID")

    DB_PATH: str = Field(..., env="DB_PATH")
    MAX_LOADS: int = Field(..., env="MAX_LOADS")

    CITIES_FILE: str = Field(..., env="CITIES_FILE")

    MAX_RETRIES: int = Field(default=3, env="MAX_RETRIES")

    ACTIVE_BOARD: int = Field(default=2, env="ACTIVE_BOARD")

    BOARD1_USERNAME: str | None = Field(default=None, env="BOARD1_USERNAME")
    BOARD1_PASSWORD: str | None = Field(default=None, env="BOARD1_PASSWORD")
    BOARD3_USERNAME: str | None = Field(default=None, env="BOARD3_USERNAME")
    BOARD3_PASSWORD: str | None = Field(default=None, env="BOARD3_PASSWORD")

    ADMIN_IDS: list[int] = Field(default=[], env="ADMIN_IDS")
    ERROR_NOTIFICATION_ENABLED: bool = Field(default=True, env="ERROR_NOTIFICATION_ENABLED")
    ERROR_NOTIFICATION_DELAY: int = Field(default=60, env="ERROR_NOTIFICATION_DELAY")

    SCRAPE_INTERVAL_SECONDS: int = Field(default=30, env="SCRAPE_INTERVAL_SECONDS")
    SCRAPE_ERROR_BACKOFF_SECONDS: int = Field(default=60, env="SCRAPE_ERROR_BACKOFF_SECONDS")
    POST_RATE_LIMIT_SECONDS: int = Field(default=3, env="POST_RATE_LIMIT_SECONDS")
    SEND_MAX_RETRIES: int = Field(default=5, env="SEND_MAX_RETRIES")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    @validator("TELEGRAM_CHANNEL_ID")
    def validate_channel_id(cls, v):
        if not (v.startswith("@") or v.lstrip("-").isdigit()):
            raise ValueError("TELEGRAM_CHANNEL_ID must start with @ or be a numeric ID")
        return v

    @validator("ACTIVE_BOARD")
    def validate_active_board(cls, v):
        if v not in (1, 2, 3):
            raise ValueError("ACTIVE_BOARD must be 1, 2, or 3")
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    return Settings()

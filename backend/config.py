from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIRECTORY = Path(__file__).resolve().parent
BACKEND_ENV_FILE = BACKEND_DIRECTORY / ".env"


class Settings(BaseSettings):
    app_name: str = "AI Growth Agent API"
    environment: str = "development"
    database_url: str = "sqlite:///./data/ai_growth_agent.db"
    frontend_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    razorpay_timeout_seconds: float = 10.0

    model_config = SettingsConfigDict(
        # Resolve from this module, never from the process working directory.
        # ``utf-8-sig`` also supports .env files saved by Windows editors with a BOM.
        env_file=str(BACKEND_ENV_FILE),
        env_file_encoding="utf-8-sig",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Personal Finance API"
    environment: str = "development"
    debug: bool = False
    database_url: str = "postgresql+psycopg://finance:finance@localhost:5432/personal_finance"
    session_cookie_name: str = "pf_session"
    session_ttl_hours: int = Field(default=168, ge=1, le=8760)
    cookie_secure: bool = False
    cors_origins: str = "http://localhost:3000"
    agent_shared_secret: str = "change-me-in-development"
    default_timezone: str = "America/Manaus"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:7b"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "Personal Finance API"
    environment: Literal["development", "test", "staging", "production"] = "development"
    debug: bool = False
    database_url: str = "postgresql+psycopg://finance:finance@localhost:5432/personal_finance"
    session_cookie_name: str = "pf_session"
    session_ttl_hours: int = Field(default=168, ge=1, le=8760)
    cookie_secure: bool = False
    cors_origins: str = "http://localhost:3000"
    allowed_hosts: str = "localhost,127.0.0.1,backend,testserver"
    agent_shared_secret: str = "change-me-in-development"
    default_timezone: str = "America/Manaus"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:7b"

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_host_list(self) -> list[str]:
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]

    @model_validator(mode="after")
    def secure_nondevelopment_defaults(self):
        if self.environment not in {"development", "test"}:
            unsafe_secrets = {"change-me-in-development", "local-agent-secret-change-me"}
            if self.agent_shared_secret in unsafe_secrets or len(self.agent_shared_secret) < 32:
                raise ValueError(
                    "Defina AGENT_SHARED_SECRET com pelo menos 32 caracteres "
                    "fora do desenvolvimento"
                )
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE deve ser true fora do ambiente de desenvolvimento")
            if self.debug:
                raise ValueError("DEBUG deve ser false fora do ambiente de desenvolvimento")
            if "*" in self.cors_origin_list or "*" in self.allowed_host_list:
                raise ValueError("CORS_ORIGINS e ALLOWED_HOSTS não podem usar * nesse ambiente")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

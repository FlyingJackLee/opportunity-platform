from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+asyncpg://opportunity:opportunity@localhost:55432/opportunity_platform"
    checkpoint_database_url: str = (
        "postgresql://opportunity:opportunity@localhost:55432/opportunity_platform"
    )
    redis_url: str = "redis://localhost:56379/0"
    llm_provider: Literal["stub", "openai_compatible"] = "stub"
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    embedding_provider: Literal["stub", "openai_compatible"] = "stub"
    embedding_api_key: str | None = None
    embedding_model: str = "text-embedding-3-small"
    embedding_base_url: str = "https://api.openai.com/v1"
    embedding_dimension: int = 1024
    collector_scheduler_enabled: bool = True
    dingtalk_webhook_url: str | None = None
    dingtalk_webhook_secret: str | None = None
    dingtalk_public_group_webhook_url: str | None = None
    dingtalk_public_group_webhook_secret: str | None = None
    log_level: str = "INFO"
    app_env: Literal["local", "test", "production"] = "local"
    cors_allow_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()

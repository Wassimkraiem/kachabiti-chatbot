import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "Kachabiti Chatbot"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"
    data_dir: Path = Path("data")
    cors_allow_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    cors_allow_origin_regex: str | None = None
    cors_allow_credentials: bool = False
    cors_allow_methods: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["*"])
    cors_allow_headers: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["*"])
    cors_expose_headers: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["X-Request-ID", "X-Process-Time"]
    )
    cors_max_age: int = Field(default=600, ge=0)

    openai_api_key: str = ""
    openai_base_url: str | None = None
    openai_chat_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_endpoint: str | None = None
    langsmith_project: str = "kachabiti-chatbot"
    langsmith_local_project: str | None = None
    langsmith_staging_project: str | None = None
    langsmith_workspace_id: str | None = None
    langsmith_prompt_name: str | None = None
    langsmith_prompt_tag: str = "latest"

    qdrant_url: str = ""
    qdrant_api_key: str | None = None
    qdrant_collection_name: str = "kachabiti"
    qdrant_timeout_seconds: float = 10.0
    embedding_dimensions: int = 1536

    chunk_size: int = Field(default=900, ge=200, le=4000)
    chunk_overlap: int = Field(default=150, ge=0, le=1000)
    default_top_k: int = Field(default=5, ge=1, le=20)
    max_upload_size_bytes: int = Field(default=10 * 1024 * 1024, ge=1024)

    @field_validator(
        "cors_allow_origins",
        "cors_allow_methods",
        "cors_allow_headers",
        "cors_expose_headers",
        mode="before",
    )
    @classmethod
    def parse_env_list(cls, value: str | list[str] | None) -> list[str] | None:
        if value is None or isinstance(value, list):
            return value
        if not isinstance(value, str):
            return value

        normalized = value.strip()
        if not normalized:
            return []
        if normalized.startswith("["):
            return json.loads(normalized)
        return [item.strip() for item in normalized.split(",") if item.strip()]

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def documents_dir(self) -> Path:
        return self.data_dir / "documents"

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"

    @property
    def resolved_langsmith_project(self) -> str:
        env_name = self.app_env.strip().lower()

        if env_name in {"local", "development", "dev"}:
            return (self.langsmith_local_project or f"{self.langsmith_project}-local").strip()
        if env_name == "staging":
            return (self.langsmith_staging_project or f"{self.langsmith_project}-staging").strip()
        return self.langsmith_project.strip()


@lru_cache
def get_settings() -> Settings:
    return Settings()

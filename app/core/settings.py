from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    openai_api_key: str = ""
    openai_base_url: str | None = None
    openai_chat_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_endpoint: str | None = None
    langsmith_project: str = "kachabiti-chatbot"
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

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def documents_dir(self) -> Path:
        return self.data_dir / "documents"

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"


@lru_cache
def get_settings() -> Settings:
    return Settings()

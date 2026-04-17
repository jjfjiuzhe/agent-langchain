from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or .env."""

    app_name: str = "Agent Retrieval API"
    environment: str = Field(default="development", description="Runtime environment, such as development or production.")
    debug: bool = True

    database_url: str = "postgresql://postgres:postgres@localhost:5432/agent"
    test_database_url: str | None = None
    pgvector_collection: str = "agent_vectors"
    pgvector_table: str = "agent_vector_items"
    task_table: str = "agent_tasks"

    openai_api_key: str | None = None
    openai_base_url: str | None = Field(default="https://api.chatanywhere.tech/v1", description="OpenAI-compatible proxy/base URL.")
    llm_model_name: str = "gpt-4o-mini"
    embedding_model_name: str = "text-embedding-3-small"
    embedding_dimension: int = 384

    project_root: Path = Field(default_factory=lambda: Path.cwd())
    docs_path: Path = Path("docs")
    code_index_path: Path = Path("app")

    retrieval_top_k: int = 5
    retrieval_score_threshold: float = 0.0
    chunk_size: int = 1000
    chunk_overlap: int = 120

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="AGENT_",
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    def resolve_docs_path(self) -> Path:
        return self._resolve_path(self.docs_path)

    def resolve_code_index_path(self) -> Path:
        return self._resolve_path(self.code_index_path)

    def _resolve_path(self, path: Path) -> Path:
        return path if path.is_absolute() else self.project_root / path


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

"""Configuration management using pydantic-settings."""

from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="RUNBOOK_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Paths
    data_dir: Path = Path("data")
    index_dir: Path = Path("data/indexes")
    database_url: str = "sqlite+aiosqlite:///data/runbook_query.db"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Retrieval
    bm25_k1: float = 1.5
    bm25_b: float = 0.75
    default_top_k: int = 10
    max_top_k: int = 50

    # Chunking
    chunk_min_tokens: int = 100
    chunk_max_tokens: int = 400
    chunk_overlap_tokens: int = 50

    # Embedding
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_batch_size: int = 32

    # Cache
    cache_max_size: int = 1000
    cache_ttl_seconds: int = 3600

    # GitHub API (optional)
    github_token: str | None = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

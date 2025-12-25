"""API Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ===== Search =====

class SearchFilters(BaseModel):
    """Filters for search requests."""

    source_types: list[Literal["docs", "issues"]] | None = None
    projects: list[str] | None = None
    tags: list[str] | None = None


class SearchRequestSchema(BaseModel):
    """Search request schema."""

    query: str = Field(..., min_length=1, max_length=500)
    filters: SearchFilters = Field(default_factory=SearchFilters)
    top_k: int = Field(default=10, ge=1, le=50)
    include_scores: bool = True


class ScoreBreakdownSchema(BaseModel):
    """Score breakdown for a search result."""

    bm25_score: float | None = None
    bm25_rank: int | None = None
    vector_score: float | None = None
    vector_rank: int | None = None
    final_score: float


class SearchResultSchema(BaseModel):
    """A single search result."""

    chunk_id: str
    document_id: str
    title: str
    snippet: str
    url: str
    source_type: Literal["docs", "issues"]
    project: str
    updated_at: datetime | None = None
    scores: ScoreBreakdownSchema | None = None


class SearchResponseSchema(BaseModel):
    """Search response schema."""

    query: str
    results: list[SearchResultSchema]
    total_results: int
    latency_ms: float
    retrieval_mode: Literal["hybrid", "bm25_only", "vector_only"]
    cache_hit: bool = False


# ===== Ingestion =====

class IngestRequestSchema(BaseModel):
    """Ingestion request schema."""

    sources: list[str] | None = None  # Source IDs to ingest, None = all
    force_reindex: bool = False


class IngestResponseSchema(BaseModel):
    """Ingestion response schema."""

    job_id: str
    status: str
    message: str


# ===== Health =====

class ComponentStatusSchema(BaseModel):
    """Status of a system component."""

    database: str = "unknown"
    bm25_index: str = "unknown"
    vector_index: str = "unknown"


class HealthResponseSchema(BaseModel):
    """Health check response schema."""

    status: str
    components: ComponentStatusSchema
    index_version: str | None = None
    chunk_count: int = 0


# ===== Metrics =====

class MetricsResponseSchema(BaseModel):
    """Metrics response schema."""

    requests_total: int = 0
    requests_by_status: dict[str, int] = Field(default_factory=dict)
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    cache_hit_rate: float = 0.0
    active_index_version: str | None = None

"""Search result models with score breakdowns."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ScoreBreakdown(BaseModel):
    """Score breakdown for a search result."""

    bm25_score: float | None = None
    bm25_rank: int | None = None
    vector_score: float | None = None
    vector_rank: int | None = None
    final_score: float = 0.0


class SearchResult(BaseModel):
    """A single search result."""

    chunk_id: str
    document_id: str
    title: str
    snippet: str  # With highlighted terms
    url: str
    source_type: Literal["docs", "issues"]
    project: str
    updated_at: datetime | None = None
    scores: ScoreBreakdown


class SearchRequest(BaseModel):
    """Search request from the API."""

    query: str
    filters: dict = {}  # source_types, projects, tags
    top_k: int = 10
    include_scores: bool = True


class SearchResponse(BaseModel):
    """Search response from the API."""

    query: str
    results: list[SearchResult]
    total_results: int
    latency_ms: float
    retrieval_mode: Literal["hybrid", "bm25_only", "vector_only"]
    cache_hit: bool = False

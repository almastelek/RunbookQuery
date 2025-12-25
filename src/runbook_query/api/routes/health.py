"""Health and metrics API routes."""

from fastapi import APIRouter

from runbook_query.api.schemas import (
    ComponentStatusSchema,
    HealthResponseSchema,
    MetricsResponseSchema,
)
from runbook_query.retrieval import get_bm25_retriever, get_query_cache, get_vector_retriever

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponseSchema)
async def health_check():
    """
    Health check endpoint.

    Returns component status and index information.
    """
    bm25 = get_bm25_retriever()
    vector = get_vector_retriever()

    components = ComponentStatusSchema(
        database="ok",  # TODO: Add actual DB health check
        bm25_index="ok" if bm25.is_ready else "not_ready",
        vector_index="ok" if vector.is_ready else "not_ready",
    )

    # Determine overall status
    if bm25.is_ready or vector.is_ready:
        status = "healthy"
    else:
        status = "degraded"

    return HealthResponseSchema(
        status=status,
        components=components,
        index_version=None,  # TODO: Track version
        chunk_count=bm25.chunk_count if bm25.is_ready else 0,
    )


@router.get("/metrics", response_model=MetricsResponseSchema)
async def get_metrics():
    """
    Get service metrics.

    Returns request counts, latencies, and cache stats.
    """
    cache = get_query_cache()

    return MetricsResponseSchema(
        requests_total=0,  # TODO: Implement request counting
        requests_by_status={},
        latency_p50_ms=0.0,  # TODO: Implement latency tracking
        latency_p95_ms=0.0,
        latency_p99_ms=0.0,
        cache_hit_rate=cache.hit_rate,
        active_index_version=None,
    )

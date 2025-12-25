"""Health and metrics API routes."""

from fastapi import APIRouter, Response

from runbook_query.api.schemas import (
    ComponentStatusSchema,
    HealthResponseSchema,
    MetricsResponseSchema,
)
from runbook_query.retrieval import get_bm25_retriever, get_query_cache, get_vector_retriever
from runbook_query.observability import get_metrics

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


@router.get("/metrics")
async def metrics():
    """Get Prometheus metrics."""
    data, content_type = get_metrics()
    return Response(content=data, media_type=content_type)

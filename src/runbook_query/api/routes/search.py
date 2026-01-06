"""Search API routes."""
from fastapi import APIRouter, Depends, HTTPException
import structlog

from runbook_query.api.schemas import (
    ScoreBreakdownSchema,
    SearchRequestSchema,
    SearchResponseSchema,
    SearchResultSchema,
)
from runbook_query.api.service import SearchService
from runbook_query.models.search import SearchRequest

router = APIRouter(prefix="/search", tags=["search"])


# Dependency injection placeholder - will be set by app factory
_search_service: SearchService | None = None


def get_search_service() -> SearchService:
    """Dependency to get search service."""
    if _search_service is None:
        raise HTTPException(status_code=503, detail="Search service not initialized")
    return _search_service


def set_search_service(service: SearchService):
    """Set the search service instance."""
    global _search_service
    _search_service = service


@router.post("", response_model=SearchResponseSchema)
async def search(
    request: SearchRequestSchema,
    service: SearchService = Depends(get_search_service),
):
    """
    Search the corpus with hybrid retrieval.

    Returns top-k results with score breakdowns and snippets.
    """
    # Convert to internal request model
    internal_request = SearchRequest(
        query=request.query,
        filters={
            "source_types": request.filters.source_types,
            "projects": request.filters.projects,
            "tags": request.filters.tags,
        },
        top_k=request.top_k,
        include_scores=request.include_scores,
    )

    logger = structlog.get_logger()

    logger.info(
        "api_search_debug",
        service_id=id(service),
        bm25_id=id(service.bm25),
        vector_id=id(service.vector if service.vector is not None else None),
        bm25_ready=service.bm25.is_ready,
        vector_ready=service.vector.is_ready if service.vector is not None else False,
        bm25_chunks=getattr(service.bm25, "chunk_count", None),
        vector_chunks=getattr(service.vector, "chunk_count", None) if service.vector is not None else 0,
        query=internal_request.query,
        top_k=internal_request.top_k,
    )

    # Perform search
    response = await service.search(internal_request)

    # Convert to API response
    results = [
        SearchResultSchema(
            chunk_id=r.chunk_id,
            document_id=r.document_id,
            title=r.title,
            snippet=r.snippet,
            url=r.url,
            source_type=r.source_type,
            project=r.project,
            updated_at=r.updated_at,
            scores=ScoreBreakdownSchema(
                bm25_score=r.scores.bm25_score,
                bm25_rank=r.scores.bm25_rank,
                vector_score=r.scores.vector_score,
                vector_rank=r.scores.vector_rank,
                final_score=r.scores.final_score,
            ) if request.include_scores else None,
        )
        for r in response.results
    ]

    return SearchResponseSchema(
        query=response.query,
        results=results,
        total_results=response.total_results,
        latency_ms=response.latency_ms,
        retrieval_mode=response.retrieval_mode,
        cache_hit=response.cache_hit,
    )

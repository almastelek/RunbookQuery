"""Search service orchestrating retrieval, caching, and result formatting."""

import re
import time
from typing import Literal

import structlog

from runbook_query.models.search import (
    ScoreBreakdown,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from runbook_query.retrieval.bm25 import BM25Retriever
from runbook_query.retrieval.cache import QueryCache
from runbook_query.retrieval.hybrid import HybridRetriever
from runbook_query.retrieval.vector import VectorRetriever
from runbook_query.storage import ChunkRepository, DocumentRepository, get_session

logger = structlog.get_logger()


class SearchService:
    """
    High-level search service.

    Orchestrates:
    - Query caching
    - Hybrid retrieval
    - Fallback handling
    - Result enrichment with metadata
    """

    def __init__(
        self,
        bm25_retriever: BM25Retriever,
        vector_retriever: VectorRetriever,
        cache: QueryCache,
    ):
        self.hybrid = HybridRetriever(bm25_retriever, vector_retriever)
        self.bm25 = bm25_retriever
        self.vector = vector_retriever
        self.cache = cache

    async def search(self, request: SearchRequest) -> SearchResponse:
        """
        Perform a search with caching and fallback.

        Args:
            request: Search request with query, filters, and top_k

        Returns:
            SearchResponse with results and metadata
        """
        start_time = time.time()
        cache_hit = False

        # Check cache
        cached = self.cache.get(
            request.query,
            request.filters,
            request.top_k,
        )
        if cached:
            from runbook_query.observability import CACHE_HITS
            CACHE_HITS.inc()
            logger.info("search_cache_hit", query=request.query)
            
            latency_ms = (time.time() - start_time) * 1000
            return SearchResponse(
                query=request.query,
                results=cached,
                total_results=len(cached),
                latency_ms=latency_ms,
                retrieval_mode="hybrid",  # Best guess for cached results
                cache_hit=True
            )

        from runbook_query.observability import CACHE_MISSES, SEARCH_REQUESTS, SEARCH_LATENCY
        CACHE_MISSES.inc()

        try:
            # Perform retrieval with fallback
            results, retrieval_mode = await self._retrieve_with_fallback(
                request.query, request.top_k
            )

            # Enrich results with document metadata
            enriched_results = await self._enrich_results(results, request.query)

            # Apply filters
            if request.filters:
                enriched_results = self._apply_filters(enriched_results, request.filters)
            
            # Cache the final enriched results
            self.cache.set(
                request.query,
                enriched_results,
                request.filters,
                request.top_k,
            )

            latency_ms = (time.time() - start_time) * 1000

            SEARCH_REQUESTS.labels(status="success", mode=retrieval_mode).inc()
            SEARCH_LATENCY.labels(mode=retrieval_mode).observe(latency_ms / 1000.0)

            logger.info(
                "search_complete",
                query=request.query,
                results_count=len(enriched_results),
                latency_ms=latency_ms,
                cache_hit=cache_hit,
                mode=retrieval_mode,
            )

            return SearchResponse(
                query=request.query,
                results=enriched_results[: request.top_k],
                total_results=len(enriched_results),
                latency_ms=latency_ms,
                retrieval_mode=retrieval_mode,
                cache_hit=cache_hit,
            )
        except Exception as e:
            SEARCH_REQUESTS.labels(status="error", mode="unknown").inc()
            raise e

    async def _retrieve_with_fallback(
        self, query: str, top_k: int
    ) -> tuple[list, Literal["hybrid", "bm25_only", "vector_only"]]:
        """
        Retrieve results with fallback to BM25 if vector fails.
        """
        try:
            if self.vector.is_ready and self.bm25.is_ready:
                results = self.hybrid.search(query, top_k=top_k)
                return results, "hybrid"
            elif self.bm25.is_ready:
                results = self.hybrid.search_bm25_only(query, top_k=top_k)
                return results, "bm25_only"
            elif self.vector.is_ready:
                results = self.hybrid.search_vector_only(query, top_k=top_k)
                return results, "vector_only"
            else:
                return [], "hybrid"
        except Exception as e:
            # Fallback to BM25 only
            logger.warning("vector_search_failed_fallback", error=str(e))
            if self.bm25.is_ready:
                results = self.hybrid.search_bm25_only(query, top_k=top_k)
                return results, "bm25_only"
            return [], "bm25_only"

    async def _enrich_results(
        self, results: list, query: str
    ) -> list[SearchResult]:
        """Enrich results with document metadata and snippets."""
        if not results:
            return []

        chunk_ids = [r.chunk_id for r in results]

        async for session in get_session():
            chunk_repo = ChunkRepository(session)
            doc_repo = DocumentRepository(session)

            # Get all chunks
            chunks = await chunk_repo.get_by_ids(chunk_ids)
            chunk_map = {c.id: c for c in chunks}

            # Get all unique documents
            doc_ids = list(set(c.document_id for c in chunks))
            docs = []
            for doc_id in doc_ids:
                doc = await doc_repo.get(doc_id)
                if doc:
                    docs.append(doc)
            doc_map = {d.id: d for d in docs}

            enriched = []
            for r in results:
                chunk = chunk_map.get(r.chunk_id)
                if not chunk:
                    continue

                doc = doc_map.get(chunk.document_id)
                if not doc:
                    continue

                # Get source info from document
                source_type = "docs"  # Default
                project = "unknown"
                if ":" in doc.source_id:
                    parts = doc.source_id.split("-")
                    if len(parts) >= 1:
                        project = parts[0]
                    if "issues" in doc.source_id:
                        source_type = "issues"

                # Create highlighted snippet
                snippet = self._highlight_snippet(chunk.content, query)

                enriched.append(SearchResult(
                    chunk_id=r.chunk_id,
                    document_id=doc.id,
                    title=doc.title,
                    snippet=snippet,
                    url=doc.url,
                    source_type=source_type,
                    project=project,
                    updated_at=doc.updated_at,
                    scores=r.breakdown,
                ))

            return enriched

    def _highlight_snippet(
        self, content: str, query: str, max_length: int = 300
    ) -> str:
        """Create a snippet with highlighted query terms."""
        # Find query terms
        query_terms = set(query.lower().split())

        # Find best window containing query terms
        words = content.split()
        best_start = 0
        best_score = 0

        window_size = 50  # words
        for i in range(len(words)):
            window = words[i : i + window_size]
            score = sum(1 for w in window if w.lower().rstrip(".,;:") in query_terms)
            if score > best_score:
                best_score = score
                best_start = i

        # Extract snippet
        snippet_words = words[best_start : best_start + window_size]
        snippet = " ".join(snippet_words)

        # Truncate if too long
        if len(snippet) > max_length:
            snippet = snippet[:max_length] + "..."

        # Add ellipsis if not at start/end
        if best_start > 0:
            snippet = "..." + snippet
        if best_start + window_size < len(words):
            snippet = snippet + "..."

        # Highlight terms with <mark>
        for term in query_terms:
            pattern = re.compile(rf"\b({re.escape(term)})\b", re.IGNORECASE)
            snippet = pattern.sub(r"<mark>\1</mark>", snippet)

        return snippet

    def _apply_filters(
        self, results: list[SearchResult], filters: dict
    ) -> list[SearchResult]:
        """Apply post-retrieval filters."""
        filtered = results

        if source_types := filters.get("source_types"):
            filtered = [r for r in filtered if r.source_type in source_types]

        if projects := filters.get("projects"):
            filtered = [r for r in filtered if r.project in projects]

        return filtered

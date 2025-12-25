"""Hybrid retrieval combining BM25 and vector search."""

from dataclasses import dataclass

from runbook_query.models.search import ScoreBreakdown
from runbook_query.retrieval.bm25 import BM25Retriever
from runbook_query.retrieval.vector import VectorRetriever


@dataclass
class HybridResult:
    """Result from hybrid search with score breakdown."""

    chunk_id: str
    final_score: float
    breakdown: ScoreBreakdown


class HybridRetriever:
    """
    Hybrid retrieval combining BM25 and vector search.

    Uses Reciprocal Rank Fusion (RRF) for merging results,
    which is robust to different score distributions.
    """

    def __init__(
        self,
        bm25_retriever: BM25Retriever,
        vector_retriever: VectorRetriever,
        rrf_k: int = 60,
        bm25_weight: float = 0.5,
        vector_weight: float = 0.5,
    ):
        """
        Initialize hybrid retriever.

        Args:
            bm25_retriever: BM25 retriever instance
            vector_retriever: Vector retriever instance
            rrf_k: RRF constant (higher = more emphasis on top ranks)
            bm25_weight: Weight for BM25 RRF scores
            vector_weight: Weight for vector RRF scores
        """
        self.bm25 = bm25_retriever
        self.vector = vector_retriever
        self.rrf_k = rrf_k
        self.bm25_weight = bm25_weight
        self.vector_weight = vector_weight

    def search(
        self,
        query: str,
        top_k: int = 10,
        fetch_k: int = 100,
    ) -> list[HybridResult]:
        """
        Perform hybrid search combining BM25 and vector retrieval.

        Args:
            query: Search query
            top_k: Number of final results to return
            fetch_k: Number of candidates to fetch from each retriever

        Returns:
            List of HybridResult with scores and breakdowns
        """
        # Get results from both retrievers
        bm25_results = self.bm25.search(query, top_k=fetch_k) if self.bm25.is_ready else []
        vector_results = self.vector.search(query, top_k=fetch_k) if self.vector.is_ready else []

        # Merge using RRF
        return self._reciprocal_rank_fusion(
            bm25_results, vector_results, top_k
        )

    def search_bm25_only(self, query: str, top_k: int = 10) -> list[HybridResult]:
        """Search using only BM25."""
        results = self.bm25.search(query, top_k=top_k)
        return [
            HybridResult(
                chunk_id=chunk_id,
                final_score=score,
                breakdown=ScoreBreakdown(
                    bm25_score=score,
                    bm25_rank=rank + 1,
                    final_score=score,
                ),
            )
            for rank, (chunk_id, score) in enumerate(results)
        ]

    def search_vector_only(self, query: str, top_k: int = 10) -> list[HybridResult]:
        """Search using only vector retrieval."""
        results = self.vector.search(query, top_k=top_k)
        return [
            HybridResult(
                chunk_id=chunk_id,
                final_score=score,
                breakdown=ScoreBreakdown(
                    vector_score=score,
                    vector_rank=rank + 1,
                    final_score=score,
                ),
            )
            for rank, (chunk_id, score) in enumerate(results)
        ]

    def _reciprocal_rank_fusion(
        self,
        bm25_results: list[tuple[str, float]],
        vector_results: list[tuple[str, float]],
        top_k: int,
    ) -> list[HybridResult]:
        """
        Merge results using Reciprocal Rank Fusion (RRF).

        RRF score = Σ (weight / (k + rank))

        This method handles different score distributions well
        and doesn't require explicit normalization.
        """
        scores: dict[str, float] = {}
        breakdowns: dict[str, ScoreBreakdown] = {}

        # Process BM25 results
        for rank, (chunk_id, score) in enumerate(bm25_results, 1):
            rrf_score = self.bm25_weight * (1.0 / (self.rrf_k + rank))
            scores[chunk_id] = scores.get(chunk_id, 0) + rrf_score
            breakdowns[chunk_id] = ScoreBreakdown(
                bm25_score=score,
                bm25_rank=rank,
                final_score=0.0,  # Will be set later
            )

        # Process vector results
        for rank, (chunk_id, score) in enumerate(vector_results, 1):
            rrf_score = self.vector_weight * (1.0 / (self.rrf_k + rank))
            scores[chunk_id] = scores.get(chunk_id, 0) + rrf_score

            if chunk_id in breakdowns:
                breakdowns[chunk_id].vector_score = score
                breakdowns[chunk_id].vector_rank = rank
            else:
                breakdowns[chunk_id] = ScoreBreakdown(
                    vector_score=score,
                    vector_rank=rank,
                    final_score=0.0,
                )

        # Sort by final RRF score
        sorted_results = sorted(scores.items(), key=lambda x: -x[1])

        # Build final results
        results = []
        for chunk_id, final_score in sorted_results[:top_k]:
            breakdown = breakdowns[chunk_id]
            breakdown.final_score = final_score
            results.append(HybridResult(
                chunk_id=chunk_id,
                final_score=final_score,
                breakdown=breakdown,
            ))

        return results

    @property
    def is_ready(self) -> bool:
        """Check if at least one retriever is ready."""
        return self.bm25.is_ready or self.vector.is_ready

    @property
    def mode(self) -> str:
        """Return the current retrieval mode based on available indexes."""
        if self.bm25.is_ready and self.vector.is_ready:
            return "hybrid"
        elif self.bm25.is_ready:
            return "bm25_only"
        elif self.vector.is_ready:
            return "vector_only"
        else:
            return "none"

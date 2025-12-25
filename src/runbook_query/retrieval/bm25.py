"""BM25 retrieval implementation using rank_bm25."""

import json
import re
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

from runbook_query.config import get_settings


class BM25Retriever:
    """
    BM25 retrieval using rank_bm25 library.

    Provides keyword-based search with TF-IDF scoring and
    document length normalization.
    """

    def __init__(self, k1: float | None = None, b: float | None = None):
        """
        Initialize BM25 retriever.

        Args:
            k1: Term frequency saturation parameter (default: 1.5)
            b: Document length normalization (default: 0.75)
        """
        settings = get_settings()
        self.k1 = k1 or settings.bm25_k1
        self.b = b or settings.bm25_b

        self._index: BM25Okapi | None = None
        self._chunk_ids: list[str] = []
        self._tokenized_corpus: list[list[str]] = []

    def build_index(self, chunks: list[tuple[str, str]]):
        """
        Build BM25 index from chunks.

        Args:
            chunks: List of (chunk_id, content) tuples
        """
        self._chunk_ids = []
        self._tokenized_corpus = []

        for chunk_id, content in chunks:
            self._chunk_ids.append(chunk_id)
            tokens = self._tokenize(content)
            self._tokenized_corpus.append(tokens)

        if self._tokenized_corpus:
            self._index = BM25Okapi(
                self._tokenized_corpus,
                k1=self.k1,
                b=self.b,
            )

    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        """
        Search the index with a query.

        Args:
            query: Search query string
            top_k: Number of results to return

        Returns:
            List of (chunk_id, score) tuples, sorted by score descending
        """
        if not self._index or not self._chunk_ids:
            return []

        # Tokenize query
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        # Get BM25 scores
        scores = self._index.get_scores(query_tokens)

        # Get top-k results
        scored_chunks = list(zip(self._chunk_ids, scores))
        scored_chunks.sort(key=lambda x: x[1], reverse=True)

        # Filter zero scores and limit to top_k
        results = [(cid, score) for cid, score in scored_chunks[:top_k] if score > 0]

        return results

    def _tokenize(self, text: str) -> list[str]:
        """
        Tokenize text into lowercase words.

        Simple tokenization that:
        - Lowercases text
        - Splits on non-alphanumeric characters
        - Removes empty tokens
        - Preserves error codes and technical terms
        """
        # Lowercase
        text = text.lower()

        # Split on whitespace and punctuation, but keep alphanumeric sequences
        tokens = re.findall(r"[a-z0-9]+", text)

        # Filter very short tokens (except common error codes)
        tokens = [t for t in tokens if len(t) > 1 or t.isdigit()]

        return tokens

    def save(self, path: Path | str):
        """
        Save the index to disk.

        Args:
            path: Path to save the index
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "k1": self.k1,
            "b": self.b,
            "chunk_ids": self._chunk_ids,
            "corpus": self._tokenized_corpus,
        }

        path.write_text(json.dumps(data))

    def load(self, path: Path | str):
        """
        Load the index from disk.

        Args:
            path: Path to load the index from
        """
        path = Path(path)
        data = json.loads(path.read_text())

        self.k1 = data["k1"]
        self.b = data["b"]
        self._chunk_ids = data["chunk_ids"]
        self._tokenized_corpus = data["corpus"]

        if self._tokenized_corpus:
            self._index = BM25Okapi(
                self._tokenized_corpus,
                k1=self.k1,
                b=self.b,
            )

    @property
    def is_ready(self) -> bool:
        """Check if the index is built and ready for search."""
        return self._index is not None and len(self._chunk_ids) > 0

    @property
    def chunk_count(self) -> int:
        """Return the number of indexed chunks."""
        return len(self._chunk_ids)


# Singleton instance
_retriever: BM25Retriever | None = None


def get_bm25_retriever() -> BM25Retriever:
    """Get the singleton BM25 retriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = BM25Retriever()
    return _retriever

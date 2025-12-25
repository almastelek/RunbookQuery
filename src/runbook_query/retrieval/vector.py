"""Vector retrieval using sentence-transformers and FAISS."""

import json
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from runbook_query.config import get_settings


class VectorRetriever:
    """
    Vector retrieval using sentence-transformers embeddings and FAISS index.

    Uses cosine similarity via normalized embeddings + inner product search.
    """

    def __init__(self, model_name: str | None = None):
        """
        Initialize vector retriever.

        Args:
            model_name: Sentence transformer model name
        """
        settings = get_settings()
        self.model_name = model_name or settings.embedding_model
        self.batch_size = settings.embedding_batch_size

        self._model: SentenceTransformer | None = None
        self._index: faiss.IndexFlatIP | None = None
        self._chunk_ids: list[str] = []
        self._embedding_dim: int = 0

    def _get_model(self) -> SentenceTransformer:
        """Lazy load the embedding model."""
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
            self._embedding_dim = self._model.get_sentence_embedding_dimension()
        return self._model

    def build_index(self, chunks: list[tuple[str, str]]):
        """
        Build FAISS index from chunks.

        Args:
            chunks: List of (chunk_id, content) tuples
        """
        if not chunks:
            return

        model = self._get_model()
        self._chunk_ids = [chunk_id for chunk_id, _ in chunks]
        contents = [content for _, content in chunks]

        # Embed all chunks
        embeddings = model.encode(
            contents,
            batch_size=self.batch_size,
            normalize_embeddings=True,  # For cosine similarity via inner product
            show_progress_bar=True,
        )

        # Build FAISS index (IndexFlatIP for inner product = cosine with normalized vectors)
        embeddings = np.array(embeddings).astype("float32")
        self._index = faiss.IndexFlatIP(self._embedding_dim)
        self._index.add(embeddings)

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

        model = self._get_model()

        # Embed query
        query_embedding = model.encode(
            [query],
            normalize_embeddings=True,
        )
        query_embedding = np.array(query_embedding).astype("float32")

        # Search
        scores, indices = self._index.search(query_embedding, min(top_k, len(self._chunk_ids)))

        # Convert to list of (chunk_id, score)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self._chunk_ids):
                results.append((self._chunk_ids[idx], float(score)))

        return results

    def embed_query(self, query: str) -> np.ndarray:
        """
        Get embedding for a query string.

        Args:
            query: Query text

        Returns:
            Normalized embedding vector
        """
        model = self._get_model()
        embedding = model.encode([query], normalize_embeddings=True)
        return np.array(embedding).astype("float32")[0]

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """
        Get embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            Array of normalized embedding vectors
        """
        model = self._get_model()
        embeddings = model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 100,
        )
        return np.array(embeddings).astype("float32")

    def save(self, index_path: Path | str, id_map_path: Path | str):
        """
        Save the index and chunk ID mapping to disk.

        Args:
            index_path: Path to save FAISS index
            id_map_path: Path to save chunk ID mapping
        """
        if not self._index:
            raise ValueError("No index to save")

        index_path = Path(index_path)
        id_map_path = Path(id_map_path)

        index_path.parent.mkdir(parents=True, exist_ok=True)
        id_map_path.parent.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self._index, str(index_path))
        id_map_path.write_text(json.dumps({
            "chunk_ids": self._chunk_ids,
            "embedding_dim": self._embedding_dim,
            "model_name": self.model_name,
        }))

    def load(self, index_path: Path | str, id_map_path: Path | str):
        """
        Load the index and chunk ID mapping from disk.

        Args:
            index_path: Path to FAISS index
            id_map_path: Path to chunk ID mapping
        """
        index_path = Path(index_path)
        id_map_path = Path(id_map_path)

        if not index_path.exists() or not id_map_path.exists():
            raise FileNotFoundError("Index files not found")

        self._index = faiss.read_index(str(index_path))

        id_map = json.loads(id_map_path.read_text())
        self._chunk_ids = id_map["chunk_ids"]
        self._embedding_dim = id_map["embedding_dim"]

    @property
    def is_ready(self) -> bool:
        """Check if the index is built and ready for search."""
        return self._index is not None and len(self._chunk_ids) > 0

    @property
    def chunk_count(self) -> int:
        """Return the number of indexed chunks."""
        return len(self._chunk_ids)


# Singleton instance
_retriever: VectorRetriever | None = None


def get_vector_retriever() -> VectorRetriever:
    """Get the singleton vector retriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = VectorRetriever()
    return _retriever

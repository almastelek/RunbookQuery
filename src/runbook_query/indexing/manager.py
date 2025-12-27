"""Index management for building, loading, and swapping indexes."""

import json
import os
from datetime import datetime
from pathlib import Path

import structlog

from runbook_query.config import get_settings
from runbook_query.retrieval.bm25 import BM25Retriever
from runbook_query.retrieval.vector import VectorRetriever
from runbook_query.storage import ChunkRepository, get_session

import zipfile
import urllib.request

logger = structlog.get_logger()


class IndexManager:
    """
    Manages BM25 and FAISS indexes.

    Features:
    - Build indexes from database chunks
    - Save/load indexes to disk
    - Atomic swap with symlinks
    - Version tracking
    """

    BM25_FILENAME = "bm25_index.json"
    FAISS_FILENAME = "vectors.faiss"
    ID_MAP_FILENAME = "chunk_id_map.json"
    CURRENT_LINK = "current"

    def __init__(
        self,
        bm25_retriever: BM25Retriever,
        vector_retriever: VectorRetriever,
        index_dir: Path | None = None,
    ):
        settings = get_settings()
        self.index_dir = index_dir or settings.index_dir
        self.bm25 = bm25_retriever
        self.vector = vector_retriever

    async def build_indexes(self, include_vectors: bool = True) -> str:
        """
        Build indexes from all chunks in the database.

        Args:
            include_vectors: Whether to build vector index (slower)

        Returns:
            Version string of the new index
        """
        version = datetime.now().strftime("v%Y%m%d_%H%M%S")
        version_dir = self.index_dir / version
        version_dir.mkdir(parents=True, exist_ok=True)

        # Load all chunks from database
        chunks = []
        async for session in get_session():
            chunk_repo = ChunkRepository(session)
            all_chunks = await chunk_repo.get_all()
            chunks = [(c.id, c.content) for c in all_chunks]

        if not chunks:
            logger.warning("no_chunks_to_index")
            return version

        logger.info("building_indexes", chunk_count=len(chunks), version=version)

        # Build BM25 index
        self.bm25.build_index(chunks)
        self.bm25.save(version_dir / self.BM25_FILENAME)
        logger.info("bm25_index_built", chunk_count=self.bm25.chunk_count)

        # Build vector index (optional, as it's slower)
        if include_vectors:
            self.vector.build_index(chunks)
            self.vector.save(
                version_dir / self.FAISS_FILENAME,
                version_dir / self.ID_MAP_FILENAME,
            )
            logger.info("vector_index_built", chunk_count=self.vector.chunk_count)

        # Activate the new version
        self._activate_version(version)

        return version

    def load_indexes(self) -> bool:
        """
        Load indexes from the current active version.

        Returns:
            True if indexes were loaded successfully
        """
        current_dir = self._get_current_dir()
        if not current_dir:
            logger.warning("no_active_index_version")
            return False

        try:
            # Load BM25
            bm25_path = current_dir / self.BM25_FILENAME
            if bm25_path.exists():
                self.bm25.load(bm25_path)
                logger.info("bm25_index_loaded", chunk_count=self.bm25.chunk_count)

            # Load FAISS
            faiss_path = current_dir / self.FAISS_FILENAME
            id_map_path = current_dir / self.ID_MAP_FILENAME
            if faiss_path.exists() and id_map_path.exists():
                self.vector.load(faiss_path, id_map_path)
                logger.info("vector_index_loaded", chunk_count=self.vector.chunk_count)

            return True

        except Exception as e:
            logger.error("index_load_failed", error=str(e))
            return False
    
    def ensure_indexes_present(self) -> bool:
        """
        Ensure index files exist locally. If missing and INDEXES_URL is set,
        download and unzip them into index_dir.
        """
        settings = get_settings()
        indexes_url = getattr(settings, "indexes_url", None)

        # Already have an active index?
        current_dir = self._get_current_dir()
        if current_dir and (current_dir / self.BM25_FILENAME).exists():
            return True

        if not indexes_url:
            logger.warning("indexes_missing_no_indexes_url")
            return False

        self.index_dir.mkdir(parents=True, exist_ok=True)
        zip_path = self.index_dir / "indexes.zip"

        logger.info("downloading_indexes", url=indexes_url)
        urllib.request.urlretrieve(indexes_url, zip_path)

        logger.info("unzipping_indexes", path=str(zip_path))
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(self.index_dir)

        try:
            zip_path.unlink()
        except Exception:
            pass

        # After unzip, try again
        current_dir = self._get_current_dir()
        ok = bool(current_dir and (current_dir / self.BM25_FILENAME).exists())
        logger.info("indexes_ready", ok=ok, current=str(current_dir) if current_dir else None)
        return ok

    def _activate_version(self, version: str):
        """Atomically activate a new index version."""
        version_dir = (self.index_dir / version).resolve()
        current_link = self.index_dir / self.CURRENT_LINK

        # Remove existing symlink if present
        if current_link.exists() or current_link.is_symlink():
            current_link.unlink()

        # Create symlink to absolute path
        current_link.symlink_to(version_dir)

        logger.info("index_version_activated", version=version)

    def _get_current_dir(self) -> Path | None:
        """Get the current active index directory."""
        current_link = self.index_dir / self.CURRENT_LINK
        if not current_link.exists():
            return None
        return current_link.resolve()

    def get_status(self) -> dict:
        """Get current index status."""
        current_dir = self._get_current_dir()
        return {
            "bm25_ready": self.bm25.is_ready,
            "bm25_chunks": self.bm25.chunk_count,
            "vector_ready": self.vector.is_ready,
            "vector_chunks": self.vector.chunk_count,
            "current_version": current_dir.name if current_dir else None,
        }


# Singleton
_manager: IndexManager | None = None


def get_index_manager(
    bm25_retriever: BM25Retriever,
    vector_retriever: VectorRetriever,
) -> IndexManager:
    """Get the singleton index manager."""
    global _manager
    if _manager is None:
        _manager = IndexManager(bm25_retriever, vector_retriever)
    return _manager

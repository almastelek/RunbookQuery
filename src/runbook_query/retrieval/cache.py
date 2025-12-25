"""LRU cache for search queries."""

import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from runbook_query.config import get_settings


@dataclass
class CacheEntry:
    """A cached search result with metadata."""

    results: Any
    created_at: float
    hits: int = 0


class QueryCache:
    """
    LRU cache for search query results.

    Features:
    - Size-limited with LRU eviction
    - TTL-based expiration
    - Cache key includes query + filters
    """

    def __init__(
        self,
        max_size: int | None = None,
        ttl_seconds: int | None = None,
    ):
        """
        Initialize the query cache.

        Args:
            max_size: Maximum number of entries to cache
            ttl_seconds: Time-to-live for cache entries in seconds
        """
        settings = get_settings()
        self.max_size = max_size or settings.cache_max_size
        self.ttl_seconds = ttl_seconds or settings.cache_ttl_seconds

        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def _make_key(self, query: str, filters: dict | None = None, top_k: int = 10) -> str:
        """Generate cache key from query parameters."""
        key_data = {
            "query": query.lower().strip(),
            "filters": filters or {},
            "top_k": top_k,
        }
        key_json = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_json.encode()).hexdigest()[:32]

    def get(self, query: str, filters: dict | None = None, top_k: int = 10) -> Any | None:
        """
        Get cached results for a query.

        Args:
            query: Search query
            filters: Search filters
            top_k: Number of results

        Returns:
            Cached results or None if not found/expired
        """
        key = self._make_key(query, filters, top_k)

        if key not in self._cache:
            self._misses += 1
            return None

        entry = self._cache[key]

        # Check TTL
        if time.time() - entry.created_at > self.ttl_seconds:
            del self._cache[key]
            self._misses += 1
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        entry.hits += 1
        self._hits += 1

        return entry.results

    def set(
        self,
        query: str,
        results: Any,
        filters: dict | None = None,
        top_k: int = 10,
    ):
        """
        Cache results for a query.

        Args:
            query: Search query
            results: Results to cache
            filters: Search filters
            top_k: Number of results
        """
        key = self._make_key(query, filters, top_k)

        # Evict oldest if at capacity
        while len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)

        self._cache[key] = CacheEntry(
            results=results,
            created_at=time.time(),
        )

    def invalidate(self):
        """Clear all cached entries."""
        self._cache.clear()

    @property
    def size(self) -> int:
        """Return current cache size."""
        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        """Return cache hit rate."""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    @property
    def stats(self) -> dict:
        """Return cache statistics."""
        return {
            "size": self.size,
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate,
        }


# Singleton instance
_cache: QueryCache | None = None


def get_query_cache() -> QueryCache:
    """Get the singleton query cache instance."""
    global _cache
    if _cache is None:
        _cache = QueryCache()
    return _cache

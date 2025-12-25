"""Observability package."""

from runbook_query.observability.metrics import (
    SEARCH_REQUESTS,
    SEARCH_LATENCY,
    CACHE_HITS,
    CACHE_MISSES,
    INGESTION_DOCUMENTS,
    INGESTION_LATENCY,
    INDEX_BUILD_TIME,
    get_metrics,
)

__all__ = [
    "SEARCH_REQUESTS",
    "SEARCH_LATENCY",
    "CACHE_HITS",
    "CACHE_MISSES",
    "INGESTION_DOCUMENTS",
    "INGESTION_LATENCY",
    "INDEX_BUILD_TIME",
    "get_metrics",
]

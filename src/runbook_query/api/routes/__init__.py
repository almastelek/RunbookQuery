"""Routes package."""

from runbook_query.api.routes.health import router as health_router
from runbook_query.api.routes.ingest import router as ingest_router
from runbook_query.api.routes.search import router as search_router

__all__ = [
    "health_router",
    "ingest_router",
    "search_router",
]

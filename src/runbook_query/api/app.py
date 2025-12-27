"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from runbook_query.api.routes import health_router, ingest_router, search_router
from runbook_query.api.routes.search import set_search_service
from runbook_query.api.service import SearchService
from runbook_query.config import get_settings
from runbook_query.indexing import get_index_manager
from runbook_query.retrieval import get_bm25_retriever, get_query_cache, get_vector_retriever
from runbook_query.storage import init_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    await init_database()

    # Initialize retrievers and load indexes
    bm25 = get_bm25_retriever()
    vector = get_vector_retriever()
    cache = get_query_cache()

    # Try to load existing indexes
    index_manager = get_index_manager(bm25, vector)
    ready = index_manager.ensure_indexes_present()
    loaded = index_manager.load_indexes()

    if not (ready and loaded):
        
        pass

    # Initialize search service
    search_service = SearchService(bm25, vector, cache)
    set_search_service(search_service)

    yield

    # Shutdown
    pass


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="RunbookQuery",
        description="Hybrid search for SRE/on-call knowledge",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS for frontend
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    app.include_router(search_router)
    app.include_router(ingest_router)
    app.include_router(health_router)

    @app.get("/")
    async def root():
        return {
            "name": "RunbookQuery",
            "version": "0.1.0",
            "docs": "/docs",
        }

    return app


# Create app instance for uvicorn
app = create_app()

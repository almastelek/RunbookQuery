"""Command-line interface for RunbookQuery."""

import argparse
import asyncio
import sys
from pathlib import Path

import structlog
import uvicorn

from runbook_query.config import get_settings
from runbook_query.ingestion import MarkdownDocsConnector, run_ingestion
from runbook_query.indexing import get_index_manager
from runbook_query.retrieval import get_bm25_retriever, get_vector_retriever
from runbook_query.storage import init_database_sync

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


def cmd_serve(args):
    """Start the API server."""
    settings = get_settings()
    host = args.host or settings.host
    port = args.port or settings.port

    logger.info("starting_server", host=host, port=port)

    uvicorn.run(
        "runbook_query.api.app:app",
        host=host,
        port=port,
        reload=args.reload,
    )


def cmd_ingest(args):
    """Run ingestion from a source."""
    logger.info("starting_ingestion", source=args.source, force=args.force)

    # Initialize database
    init_database_sync()

    source_path = Path(args.source)
    if not source_path.exists():
        logger.error("source_not_found", path=str(source_path))
        sys.exit(1)

    # Create connector
    source_id = args.name or source_path.name
    connector = MarkdownDocsConnector(
        source_id=f"{source_id}-docs",
        project=source_id,
        docs_path=source_path,
        base_url=args.base_url,
    )

    # Run ingestion
    stats = asyncio.run(run_ingestion([connector], force=args.force))

    for s in stats:
        logger.info(
            "ingestion_complete",
            source=s.source_id,
            created=s.documents_created,
            updated=s.documents_updated,
            skipped=s.documents_skipped,
            chunks=s.chunks_created,
            errors=s.errors,
            duration=f"{s.duration_seconds:.2f}s",
        )


def cmd_build_index(args):
    """Build search indexes from database."""
    logger.info("building_indexes", include_vectors=not args.bm25_only)

    # Initialize components
    init_database_sync()
    bm25 = get_bm25_retriever()
    vector = get_vector_retriever()
    manager = get_index_manager(bm25, vector)

    # Build indexes
    version = asyncio.run(manager.build_indexes(include_vectors=not args.bm25_only))

    logger.info(
        "indexes_built",
        version=version,
        bm25_chunks=bm25.chunk_count,
        vector_chunks=vector.chunk_count if not args.bm25_only else 0,
    )


def cmd_search(args):
    """Test search from command line."""
    from runbook_query.retrieval import get_query_cache
    from runbook_query.api.service import SearchService
    from runbook_query.models.search import SearchRequest

    # Initialize
    init_database_sync()
    bm25 = get_bm25_retriever()
    vector = get_vector_retriever()
    cache = get_query_cache()
    manager = get_index_manager(bm25, vector)

    # Load indexes
    if not manager.load_indexes():
        logger.error("no_indexes_found", hint="Run 'runbook-query build-index' first")
        sys.exit(1)

    # Create service and search
    service = SearchService(bm25, vector, cache)
    request = SearchRequest(query=args.query, top_k=args.top_k)
    response = asyncio.run(service.search(request))

    # Print results
    print(f"\n Query: {args.query}")
    print(f" Mode: {response.retrieval_mode} | Latency: {response.latency_ms:.1f}ms\n")

    for i, result in enumerate(response.results, 1):
        print(f"{i}. {result.title}")
        print(f"    {result.source_type} | {result.project}")
        print(f"    {result.url}")
        print(f"    Score: {result.scores.final_score:.4f}")
        if result.scores.bm25_score is not None:
            print(f"     BM25: {result.scores.bm25_score:.4f} (rank {result.scores.bm25_rank})")
        if result.scores.vector_score is not None:
            print(f"     Vector: {result.scores.vector_score:.4f} (rank {result.scores.vector_rank})")
        # Clean snippet of HTML tags for terminal
        snippet = result.snippet.replace("<mark>", "\033[1;33m").replace("</mark>", "\033[0m")
        print(f"   {snippet[:200]}...")
        print()


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        prog="runbook-query",
        description="Hybrid search for SRE/on-call knowledge",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # serve command
    serve_parser = subparsers.add_parser("serve", help="Start the API server")
    serve_parser.add_argument("--host", type=str, help="Host to bind to")
    serve_parser.add_argument("--port", type=int, help="Port to bind to")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    serve_parser.set_defaults(func=cmd_serve)

    # ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest documents from a source")
    ingest_parser.add_argument("--source", "-s", required=True, help="Path to docs directory")
    ingest_parser.add_argument("--name", "-n", help="Source name (defaults to directory name)")
    ingest_parser.add_argument("--base-url", help="Base URL for doc links")
    ingest_parser.add_argument("--force", "-f", action="store_true", help="Force reprocess all")
    ingest_parser.set_defaults(func=cmd_ingest)

    # build-index command
    build_parser = subparsers.add_parser("build-index", help="Build search indexes")
    build_parser.add_argument("--bm25-only", action="store_true", help="Build only BM25 index")
    build_parser.set_defaults(func=cmd_build_index)

    # search command
    search_parser = subparsers.add_parser("search", help="Test search from CLI")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--top-k", "-k", type=int, default=5, help="Number of results")
    search_parser.set_defaults(func=cmd_search)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

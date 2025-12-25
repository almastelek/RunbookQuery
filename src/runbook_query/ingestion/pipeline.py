"""Ingestion pipeline orchestration."""

import asyncio
from dataclasses import dataclass
from datetime import datetime

import structlog

from runbook_query.ingestion.chunker import get_chunker
from runbook_query.ingestion.connectors.base import BaseConnector
from runbook_query.ingestion.parser import get_parser
from runbook_query.models.document import Source
from runbook_query.storage import (
    ChunkRepository,
    DocumentRepository,
    SourceRepository,
    compute_content_hash,
    get_session,
    init_database,
)

logger = structlog.get_logger()


@dataclass
class IngestStats:
    """Statistics from an ingestion run."""

    source_id: str
    documents_processed: int = 0
    documents_created: int = 0
    documents_updated: int = 0
    documents_skipped: int = 0
    chunks_created: int = 0
    errors: int = 0
    duration_seconds: float = 0.0


class IngestionPipeline:
    """
    Orchestrates the ingestion of documents from connectors.

    Flow:
    1. Fetch documents from connector
    2. Check if document changed (content hash)
    3. Parse and chunk new/changed documents
    4. Store in database
    """

    def __init__(self):
        self.parser = get_parser()
        self.chunker = get_chunker()

    async def ingest(self, connector: BaseConnector, force: bool = False) -> IngestStats:
        """
        Ingest all documents from a connector.

        Args:
            connector: The data source connector
            force: If True, reprocess all documents regardless of hash

        Returns:
            IngestStats with counts of processed documents
        """
        start_time = datetime.utcnow()
        stats = IngestStats(source_id=connector.source_id)

        # Initialize database
        await init_database()

        async for session in get_session():
            source_repo = SourceRepository(session)
            doc_repo = DocumentRepository(session)
            chunk_repo = ChunkRepository(session)

            # Ensure source exists
            source = Source(
                id=connector.source_id,
                name=connector.source_name,
                type=connector.source_type,
                project=connector.project,
            )
            await source_repo.upsert(source)

            # Process documents
            async for raw_doc in connector.fetch_documents():
                try:
                    result = await self._process_document(
                        raw_doc, doc_repo, chunk_repo, force
                    )
                    stats.documents_processed += 1

                    if result == "created":
                        stats.documents_created += 1
                    elif result == "updated":
                        stats.documents_updated += 1
                    elif result == "skipped":
                        stats.documents_skipped += 1

                    # Count chunks if document was processed
                    if result in ("created", "updated"):
                        doc_id = f"{raw_doc.source_id}:{raw_doc.external_id}"
                        chunks = await chunk_repo.get_by_document(doc_id)
                        stats.chunks_created += len(chunks)

                    logger.debug(
                        "processed_document",
                        doc_id=f"{raw_doc.source_id}:{raw_doc.external_id}",
                        result=result,
                    )

                except Exception as e:
                    stats.errors += 1
                    logger.error(
                        "document_processing_error",
                        doc_id=f"{raw_doc.source_id}:{raw_doc.external_id}",
                        error=str(e),
                    )

        stats.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            "ingestion_complete",
            source_id=connector.source_id,
            stats=stats.__dict__,
        )

        return stats

    async def _process_document(
        self,
        raw_doc,
        doc_repo: DocumentRepository,
        chunk_repo: ChunkRepository,
        force: bool,
    ) -> str:
        """
        Process a single document.

        Returns:
            "created", "updated", or "skipped"
        """
        content_hash = compute_content_hash(raw_doc.content)
        doc_id = f"{raw_doc.source_id}:{raw_doc.external_id}"

        # Check if document exists and has same hash
        existing = await doc_repo.get(doc_id)
        if existing and existing.content_hash == content_hash and not force:
            return "skipped"

        # Delete existing chunks if updating
        if existing:
            await chunk_repo.delete_by_document(doc_id)
            status = "updated"
        else:
            status = "created"

        # Parse and chunk
        parsed = self.parser.parse(raw_doc.content)
        chunks = self.chunker.chunk(parsed, doc_id)

        # Save document
        await doc_repo.upsert(raw_doc, content_hash)

        # Save chunks
        if chunks:
            await chunk_repo.create_many(chunks)

        return status


async def run_ingestion(
    connectors: list[BaseConnector], force: bool = False
) -> list[IngestStats]:
    """
    Run ingestion for multiple connectors.

    Args:
        connectors: List of connectors to ingest from
        force: If True, reprocess all documents

    Returns:
        List of IngestStats for each connector
    """
    pipeline = IngestionPipeline()
    results = []

    for connector in connectors:
        logger.info("starting_ingestion", source_id=connector.source_id)
        stats = await pipeline.ingest(connector, force=force)
        results.append(stats)

    return results

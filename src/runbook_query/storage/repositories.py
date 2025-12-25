"""Repository pattern for database operations."""

import hashlib
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from runbook_query.models.document import Chunk, Document, RawDocument, Source
from runbook_query.storage.database import ChunkORM, DocumentORM, SourceORM


class SourceRepository:
    """Repository for source CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, source_id: str) -> Source | None:
        """Get a source by ID."""
        result = await self.session.execute(
            select(SourceORM).where(SourceORM.id == source_id)
        )
        orm = result.scalar_one_or_none()
        return self._to_model(orm) if orm else None

    async def get_all(self) -> list[Source]:
        """Get all sources."""
        result = await self.session.execute(select(SourceORM))
        return [self._to_model(orm) for orm in result.scalars()]

    async def create(self, source: Source) -> Source:
        """Create a new source."""
        orm = SourceORM(
            id=source.id,
            name=source.name,
            type=source.type,
            project=source.project,
            base_url=source.base_url,
        )
        self.session.add(orm)
        await self.session.commit()
        return source

    async def upsert(self, source: Source) -> Source:
        """Create or update a source."""
        existing = await self.get(source.id)
        if existing:
            await self.session.execute(
                SourceORM.__table__.update()
                .where(SourceORM.id == source.id)
                .values(
                    name=source.name,
                    type=source.type,
                    project=source.project,
                    base_url=source.base_url,
                    updated_at=datetime.utcnow(),
                )
            )
            await self.session.commit()
            return source
        return await self.create(source)

    def _to_model(self, orm: SourceORM) -> Source:
        return Source(
            id=orm.id,
            name=orm.name,
            type=orm.type,
            project=orm.project,
            base_url=orm.base_url,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )


class DocumentRepository:
    """Repository for document CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, doc_id: str) -> Document | None:
        """Get a document by ID."""
        result = await self.session.execute(
            select(DocumentORM).where(DocumentORM.id == doc_id)
        )
        orm = result.scalar_one_or_none()
        return self._to_model(orm) if orm else None

    async def get_by_source_and_external_id(
        self, source_id: str, external_id: str
    ) -> Document | None:
        """Get a document by source and external ID."""
        doc_id = f"{source_id}:{external_id}"
        return await self.get(doc_id)

    async def get_all(self, source_id: str | None = None) -> list[Document]:
        """Get all documents, optionally filtered by source."""
        query = select(DocumentORM)
        if source_id:
            query = query.where(DocumentORM.source_id == source_id)
        result = await self.session.execute(query)
        return [self._to_model(orm) for orm in result.scalars()]

    async def upsert(self, raw_doc: RawDocument, content_hash: str) -> Document:
        """Create or update a document."""
        doc_id = f"{raw_doc.source_id}:{raw_doc.external_id}"
        existing = await self.get(doc_id)

        if existing:
            # Update existing document
            await self.session.execute(
                DocumentORM.__table__.update()
                .where(DocumentORM.id == doc_id)
                .values(
                    title=raw_doc.title,
                    url=raw_doc.url,
                    raw_content=raw_doc.content,
                    content_hash=content_hash,
                    doc_metadata=raw_doc.metadata,
                    updated_at=datetime.utcnow(),
                )
            )
            await self.session.commit()
        else:
            # Create new document
            orm = DocumentORM(
                id=doc_id,
                source_id=raw_doc.source_id,
                external_id=raw_doc.external_id,
                title=raw_doc.title,
                url=raw_doc.url,
                raw_content=raw_doc.content,
                content_hash=content_hash,
                doc_metadata=raw_doc.metadata,
            )
            self.session.add(orm)
            await self.session.commit()

        return Document(
            id=doc_id,
            source_id=raw_doc.source_id,
            external_id=raw_doc.external_id,
            title=raw_doc.title,
            url=raw_doc.url,
            raw_content=raw_doc.content,
            content_hash=content_hash,
            metadata=raw_doc.metadata,
        )

    async def delete(self, doc_id: str) -> bool:
        """Delete a document and its chunks."""
        result = await self.session.execute(
            delete(DocumentORM).where(DocumentORM.id == doc_id)
        )
        await self.session.commit()
        return result.rowcount > 0

    def _to_model(self, orm: DocumentORM) -> Document:
        return Document(
            id=orm.id,
            source_id=orm.source_id,
            external_id=orm.external_id,
            title=orm.title,
            url=orm.url,
            raw_content=orm.raw_content,
            content_hash=orm.content_hash,
            metadata=orm.doc_metadata or {},
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )


class ChunkRepository:
    """Repository for chunk CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, chunk_id: str) -> Chunk | None:
        """Get a chunk by ID."""
        result = await self.session.execute(
            select(ChunkORM).where(ChunkORM.id == chunk_id)
        )
        orm = result.scalar_one_or_none()
        return self._to_model(orm) if orm else None

    async def get_by_document(self, document_id: str) -> list[Chunk]:
        """Get all chunks for a document."""
        result = await self.session.execute(
            select(ChunkORM)
            .where(ChunkORM.document_id == document_id)
            .order_by(ChunkORM.chunk_index)
        )
        return [self._to_model(orm) for orm in result.scalars()]

    async def get_all(self) -> list[Chunk]:
        """Get all chunks."""
        result = await self.session.execute(select(ChunkORM))
        return [self._to_model(orm) for orm in result.scalars()]

    async def get_by_ids(self, chunk_ids: list[str]) -> list[Chunk]:
        """Get chunks by a list of IDs."""
        if not chunk_ids:
            return []
        result = await self.session.execute(
            select(ChunkORM).where(ChunkORM.id.in_(chunk_ids))
        )
        return [self._to_model(orm) for orm in result.scalars()]

    async def create(self, chunk: Chunk) -> Chunk:
        """Create a new chunk."""
        orm = ChunkORM(
            id=chunk.id,
            document_id=chunk.document_id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            content_hash=chunk.content_hash,
            heading_path=chunk.heading_path,
            start_offset=chunk.start_offset,
            end_offset=chunk.end_offset,
            token_count=chunk.token_count,
            embedding_id=chunk.embedding_id,
        )
        self.session.add(orm)
        await self.session.commit()
        return chunk

    async def create_many(self, chunks: list[Chunk]) -> list[Chunk]:
        """Create multiple chunks."""
        for chunk in chunks:
            orm = ChunkORM(
                id=chunk.id,
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                content_hash=chunk.content_hash,
                heading_path=chunk.heading_path,
                start_offset=chunk.start_offset,
                end_offset=chunk.end_offset,
                token_count=chunk.token_count,
                embedding_id=chunk.embedding_id,
            )
            self.session.add(orm)
        await self.session.commit()
        return chunks

    async def delete_by_document(self, document_id: str) -> int:
        """Delete all chunks for a document."""
        result = await self.session.execute(
            delete(ChunkORM).where(ChunkORM.document_id == document_id)
        )
        await self.session.commit()
        return result.rowcount

    async def count(self) -> int:
        """Count total chunks."""
        from sqlalchemy import func
        result = await self.session.execute(select(func.count(ChunkORM.id)))
        return result.scalar() or 0

    def _to_model(self, orm: ChunkORM) -> Chunk:
        return Chunk(
            id=orm.id,
            document_id=orm.document_id,
            chunk_index=orm.chunk_index,
            content=orm.content,
            content_hash=orm.content_hash,
            heading_path=orm.heading_path,
            start_offset=orm.start_offset,
            end_offset=orm.end_offset,
            token_count=orm.token_count,
            embedding_id=orm.embedding_id,
            created_at=orm.created_at,
        )


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of content."""
    return hashlib.sha256(content.encode()).hexdigest()

"""Database setup with SQLAlchemy async support (SQLite for local, Postgres for prod)."""

from __future__ import annotations

from typing import AsyncGenerator, Optional

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy import JSON as SA_JSON
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship

try:
    # Optional: enables JSONB automatically on Postgres
    from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
except Exception:  # pragma: no cover
    PG_JSONB = None

from runbook_query.config import get_settings


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


def _json_type():
    """
    Use JSONB on Postgres when available, otherwise JSON.
    Keeps models portable across SQLite/Postgres.
    """
    if PG_JSONB is None:
        return SA_JSON
    return SA_JSON().with_variant(PG_JSONB, "postgresql")


class SourceORM(Base):
    """Sources table - where documents come from."""

    __tablename__ = "sources"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # "docs" | "issues"
    project = Column(String, nullable=False)
    base_url = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    documents = relationship(
        "DocumentORM",
        back_populates="source",
        cascade="all, delete-orphan",
    )


class DocumentORM(Base):
    """Documents table - individual pages/issues."""

    __tablename__ = "documents"

    id = Column(String, primary_key=True)  # "{source_id}:{external_id}"
    source_id = Column(String, ForeignKey("sources.id"), nullable=False)
    external_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    raw_content = Column(Text, nullable=True)
    content_hash = Column(String, nullable=False)

    # Named doc_metadata to avoid clashing with SQLAlchemy's "metadata"
    doc_metadata = Column(_json_type(), default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    source = relationship("SourceORM", back_populates="documents")
    chunks = relationship("ChunkORM", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_documents_source", "source_id"),
        Index("idx_documents_hash", "content_hash"),
        # If you want parity with your SQL schema:
        # UniqueConstraint("source_id", "external_id", name="uq_documents_source_external")
    )


class ChunkORM(Base):
    """Chunks table - searchable units."""

    __tablename__ = "chunks"

    id = Column(String, primary_key=True)  # "{doc_id}:{chunk_hash}"
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)

    content = Column(Text, nullable=False)
    content_hash = Column(String, nullable=False)

    heading_path = Column(String, nullable=True)
    start_offset = Column(Integer, nullable=True)
    end_offset = Column(Integer, nullable=True)

    token_count = Column(Integer, default=0, nullable=False)
    embedding_id = Column(Integer, nullable=True)  # Position in FAISS index

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    document = relationship("DocumentORM", back_populates="chunks")

    __table_args__ = (
        Index("idx_chunks_document", "document_id"),
        Index("idx_chunks_hash", "content_hash"),
        # If you want strict uniqueness like your SQL schema:
        # UniqueConstraint("document_id", "chunk_index", name="uq_chunks_doc_chunk_index")
    )


class IndexVersionORM(Base):
    """Index versions table - tracks BM25 and FAISS index files."""

    __tablename__ = "index_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String, nullable=False)
    bm25_path = Column(String, nullable=True)
    faiss_path = Column(String, nullable=True)
    chunk_count = Column(Integer, default=0, nullable=False)
    status = Column(String, default="building", nullable=False)  # "building" | "ready" | "deprecated"

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


_async_engine = None
_async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


async def get_async_engine():
    """Get or create the async database engine."""
    global _async_engine
    if _async_engine is None:
        settings = get_settings()
        db_url = settings.database_url

        engine_kwargs = {
            "echo": settings.debug,
        }

        # Pooling options should NOT be forced on SQLite.
        if not _is_sqlite(db_url):
            engine_kwargs.update(
                {
                    "pool_pre_ping": True,
                    # Keep small for free tiers / Render
                    "pool_size": 5,
                    "max_overflow": 5,
                }
            )

        _async_engine = create_async_engine(db_url, **engine_kwargs)

    return _async_engine


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    global _async_session_factory
    if _async_session_factory is None:
        engine = await get_async_engine()
        _async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with _async_session_factory() as session:
        yield session


async def init_database():
    """
    Initialize the database, creating tables if they don't exist.

    For production, you may later prefer Alembic migrations;
    for a demo, create_all is usually fine if you control schema changes.
    """
    engine = await get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def init_database_sync():
    """
    Synchronously initialize DB (for CLI scripts / one-off seeding).
    Converts async DB URLs to sync driver equivalents.
    """
    settings = get_settings()
    url = make_url(settings.database_url)

    # SQLite async -> sqlite sync
    if url.drivername.endswith("+aiosqlite"):
        url = url.set(drivername="sqlite")

    # Postgres asyncpg -> psycopg (recommended sync driver)
    elif url.drivername.endswith("+asyncpg"):
        url = url.set(drivername="postgresql+psycopg")

    # If someone uses other async drivers, you can extend mappings here.

    engine = create_engine(url, echo=settings.debug, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    return engine

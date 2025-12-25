"""SQLite database setup with SQLAlchemy async support."""
# changing to postgresql

from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship

from runbook_query.config import get_settings


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class SourceORM(Base):
    """Sources table - where documents come from."""

    __tablename__ = "sources"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # "docs" | "issues"
    project = Column(String, nullable=False)
    base_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = relationship("DocumentORM", back_populates="source", cascade="all, delete-orphan")


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
    doc_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    source = relationship("SourceORM", back_populates="documents")
    chunks = relationship("ChunkORM", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_documents_source", "source_id"),
        Index("idx_documents_hash", "content_hash"),
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
    token_count = Column(Integer, default=0)
    embedding_id = Column(Integer, nullable=True)  # Position in FAISS index
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("DocumentORM", back_populates="chunks")

    __table_args__ = (
        Index("idx_chunks_document", "document_id"),
        Index("idx_chunks_hash", "content_hash"),
    )


class IndexVersionORM(Base):
    """Index versions table - tracks BM25 and FAISS index files."""

    __tablename__ = "index_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String, nullable=False)
    bm25_path = Column(String, nullable=True)
    faiss_path = Column(String, nullable=True)
    chunk_count = Column(Integer, default=0)
    status = Column(String, default="building")  # "building" | "ready" | "deprecated"
    created_at = Column(DateTime, default=datetime.utcnow)


# Async engine and session factory
_async_engine = None
_async_session_factory = None


async def get_async_engine():
    """Get or create the async database engine."""
    global _async_engine
    if _async_engine is None:
        settings = get_settings()
        _async_engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
        )
    return _async_engine


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session."""
    global _async_session_factory
    if _async_session_factory is None:
        engine = await get_async_engine()
        _async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with _async_session_factory() as session:
        yield session


async def init_database():
    """Initialize the database, creating tables if they don't exist."""
    engine = await get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def init_database_sync():
    """Synchronously initialize the database (for CLI)."""
    settings = get_settings()
    # Convert async URL to sync URL
    sync_url = settings.database_url.replace("+aiosqlite", "")
    engine = create_engine(sync_url)
    Base.metadata.create_all(engine)
    return engine

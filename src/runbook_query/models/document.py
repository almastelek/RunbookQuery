"""Data models for documents, chunks, and sources."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Source(BaseModel):
    """A data source (e.g., kubernetes-docs, prometheus-issues)."""

    id: str
    name: str
    type: Literal["docs", "issues"]
    project: str
    base_url: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Document(BaseModel):
    """A document from a source (a doc page or GitHub issue)."""

    id: str  # "{source_id}:{external_id}"
    source_id: str
    external_id: str
    title: str
    url: str
    raw_content: str | None = None
    content_hash: str
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Chunk(BaseModel):
    """A searchable chunk of a document."""

    id: str  # "{doc_id}:{chunk_hash}"
    document_id: str
    chunk_index: int
    content: str
    content_hash: str
    heading_path: str | None = None
    start_offset: int | None = None
    end_offset: int | None = None
    token_count: int = 0
    embedding_id: int | None = None  # Position in FAISS index
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RawDocument(BaseModel):
    """Raw document fetched from a connector before processing."""

    source_id: str
    external_id: str
    title: str
    content: str
    url: str
    metadata: dict = Field(default_factory=dict)


class ParsedDocument(BaseModel):
    """Document after parsing markdown."""

    text: str
    headings: list[tuple[int, str, int]] = Field(default_factory=list)  # (level, text, offset)
    code_blocks: list[str] = Field(default_factory=list)

"""Ingestion package."""

from runbook_query.ingestion.chunker import HeadingChunker, get_chunker
from runbook_query.ingestion.connectors import (
    BaseConnector,
    GitHubIssuesConnector,
    MarkdownDocsConnector,
)
from runbook_query.ingestion.parser import MarkdownParser, get_parser
from runbook_query.ingestion.pipeline import IngestionPipeline, IngestStats, run_ingestion

__all__ = [
    "BaseConnector",
    "GitHubIssuesConnector",
    "HeadingChunker",
    "IngestionPipeline",
    "IngestStats",
    "MarkdownDocsConnector",
    "MarkdownParser",
    "get_chunker",
    "get_parser",
    "run_ingestion",
]

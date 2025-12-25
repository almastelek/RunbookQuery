"""Abstract base connector interface for data sources."""

from abc import ABC, abstractmethod
from typing import AsyncIterator

from runbook_query.models.document import RawDocument


class BaseConnector(ABC):
    """Abstract base class for data source connectors."""

    def __init__(self, source_id: str, project: str):
        self.source_id = source_id
        self.project = project

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Return the source type ('docs' or 'issues')."""
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return a human-readable name for the source."""
        pass

    @abstractmethod
    async def fetch_documents(self) -> AsyncIterator[RawDocument]:
        """
        Fetch documents from this source.

        Yields RawDocument objects containing the document content.
        """
        pass

    async def __aiter__(self):
        """Allow async iteration over documents."""
        async for doc in self.fetch_documents():
            yield doc

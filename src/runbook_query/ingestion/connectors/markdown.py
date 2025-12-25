"""Markdown documentation connector for local or remote markdown files."""

import re
from pathlib import Path
from typing import AsyncIterator
from urllib.parse import urljoin

from runbook_query.ingestion.connectors.base import BaseConnector
from runbook_query.models.document import RawDocument


class MarkdownDocsConnector(BaseConnector):
    """
    Connector for markdown documentation files.

    Supports local directories of markdown files. Can be extended
    to support remote git repos.
    """

    def __init__(
        self,
        source_id: str,
        project: str,
        docs_path: str | Path,
        base_url: str | None = None,
        glob_pattern: str = "**/*.md",
        exclude_patterns: list[str] | None = None,
    ):
        """
        Initialize the markdown docs connector.

        Args:
            source_id: Unique identifier for this source
            project: Project name (e.g., "kubernetes", "prometheus")
            docs_path: Path to the documentation directory
            base_url: Base URL for constructing documentation links
            glob_pattern: Glob pattern for finding markdown files
            exclude_patterns: Patterns to exclude (e.g., ["**/node_modules/**"])
        """
        super().__init__(source_id, project)
        self.docs_path = Path(docs_path)
        self.base_url = base_url
        self.glob_pattern = glob_pattern
        self.exclude_patterns = exclude_patterns or []

    @property
    def source_type(self) -> str:
        return "docs"

    @property
    def source_name(self) -> str:
        return f"{self.project.title()} Documentation"

    async def fetch_documents(self) -> AsyncIterator[RawDocument]:
        """Fetch all markdown files from the docs directory."""
        if not self.docs_path.exists():
            raise FileNotFoundError(f"Docs path not found: {self.docs_path}")

        for file_path in self.docs_path.glob(self.glob_pattern):
            # Skip excluded patterns
            if self._should_exclude(file_path):
                continue

            # Skip non-files
            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                # Skip binary files
                continue

            # Extract title from content
            title = self._extract_title(content, file_path)

            # Generate URL
            relative_path = file_path.relative_to(self.docs_path)
            url = self._generate_url(relative_path)

            yield RawDocument(
                source_id=self.source_id,
                external_id=str(relative_path),
                title=title,
                content=content,
                url=url,
                metadata={
                    "file_path": str(file_path),
                    "relative_path": str(relative_path),
                },
            )

    def _should_exclude(self, file_path: Path) -> bool:
        """Check if a file should be excluded based on patterns."""
        path_str = str(file_path)
        for pattern in self.exclude_patterns:
            if Path(path_str).match(pattern):
                return True
        return False

    def _extract_title(self, content: str, file_path: Path) -> str:
        """Extract title from markdown content or use filename."""
        # Try to find H1 heading
        h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if h1_match:
            return h1_match.group(1).strip()

        # Try to find title in YAML front matter
        front_matter_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if front_matter_match:
            front_matter = front_matter_match.group(1)
            title_match = re.search(r"^title:\s*['\"]?(.+?)['\"]?\s*$", front_matter, re.MULTILINE)
            if title_match:
                return title_match.group(1).strip()

        # Fallback to filename
        return file_path.stem.replace("-", " ").replace("_", " ").title()

    def _generate_url(self, relative_path: Path) -> str:
        """Generate a URL for the document."""
        if self.base_url:
            # Convert .md to .html or remove extension for web URLs
            url_path = str(relative_path).replace(".md", "")
            return urljoin(self.base_url, url_path)
        else:
            # Use file:// URL for local files
            return f"file://{self.docs_path / relative_path}"

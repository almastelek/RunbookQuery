"""Markdown parser for extracting structured text."""

import re
from dataclasses import dataclass

from runbook_query.models.document import ParsedDocument


@dataclass
class Heading:
    """A markdown heading with level, text, and offset."""

    level: int
    text: str
    offset: int


class MarkdownParser:
    """Parse markdown content into structured text."""

    # Regex patterns
    FRONT_MATTER_PATTERN = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)
    HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    CODE_BLOCK_PATTERN = re.compile(r"```[\w]*\n(.*?)```", re.DOTALL)
    INLINE_CODE_PATTERN = re.compile(r"`([^`]+)`")
    LINK_PATTERN = re.compile(r"\[([^\]]+)\]\([^)]+\)")
    IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\([^)]+\)")
    HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
    BOLD_PATTERN = re.compile(r"\*\*([^*]+)\*\*")
    ITALIC_PATTERN = re.compile(r"\*([^*]+)\*")
    BULLET_PATTERN = re.compile(r"^[\s]*[-*+]\s+", re.MULTILINE)
    NUMBERED_PATTERN = re.compile(r"^[\s]*\d+\.\s+", re.MULTILINE)

    def parse(self, content: str) -> ParsedDocument:
        """
        Parse markdown content into structured text.

        Args:
            content: Raw markdown content

        Returns:
            ParsedDocument with text, headings, and code blocks
        """
        # Strip front matter (YAML metadata)
        content = self._strip_front_matter(content)

        # Extract headings with their positions
        headings = self._extract_headings(content)

        # Extract code blocks (preserve for context)
        code_blocks = self._extract_code_blocks(content)

        # Convert to plain text
        text = self._to_plaintext(content)

        return ParsedDocument(
            text=text,
            headings=[(h.level, h.text, h.offset) for h in headings],
            code_blocks=code_blocks,
        )

    def _strip_front_matter(self, content: str) -> str:
        """Remove YAML front matter from content."""
        return self.FRONT_MATTER_PATTERN.sub("", content)

    def _extract_headings(self, content: str) -> list[Heading]:
        """Extract all headings with their levels and positions."""
        headings = []
        for match in self.HEADING_PATTERN.finditer(content):
            level = len(match.group(1))
            text = match.group(2).strip()
            offset = match.start()
            headings.append(Heading(level=level, text=text, offset=offset))
        return headings

    def _extract_code_blocks(self, content: str) -> list[str]:
        """Extract fenced code block contents."""
        return self.CODE_BLOCK_PATTERN.findall(content)

    def _to_plaintext(self, content: str) -> str:
        """
        Convert markdown to plain text while preserving structure.

        Keeps code blocks as they often contain important information
        like error messages and commands.
        """
        text = content

        # Replace code blocks with their content (preserve for search)
        # Format: keep the code but remove the fence markers
        text = re.sub(r"```[\w]*\n", "\n", text)
        text = re.sub(r"```", "", text)

        # Replace images with alt text
        text = self.IMAGE_PATTERN.sub(r"[Image: \1]", text)

        # Replace links with just the text
        text = self.LINK_PATTERN.sub(r"\1", text)

        # Remove HTML tags
        text = self.HTML_TAG_PATTERN.sub("", text)

        # Remove bold/italic markers but keep text
        text = self.BOLD_PATTERN.sub(r"\1", text)
        text = self.ITALIC_PATTERN.sub(r"\1", text)

        # Keep inline code content
        text = self.INLINE_CODE_PATTERN.sub(r"\1", text)

        # Clean up bullet points (keep content)
        text = self.BULLET_PATTERN.sub("- ", text)
        text = self.NUMBERED_PATTERN.sub("", text)

        # Remove heading markers but keep text
        text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)

        # Clean up excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = text.strip()

        return text


# Singleton parser instance
_parser = None


def get_parser() -> MarkdownParser:
    """Get the singleton parser instance."""
    global _parser
    if _parser is None:
        _parser = MarkdownParser()
    return _parser

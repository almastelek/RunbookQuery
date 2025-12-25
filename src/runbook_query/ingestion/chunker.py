"""Heading-aware chunker for splitting documents."""

import hashlib
import re
from dataclasses import dataclass

import tiktoken

from runbook_query.config import get_settings
from runbook_query.models.document import Chunk, ParsedDocument


@dataclass
class Section:
    """A section of a document with heading context."""

    text: str
    heading_path: str
    start_offset: int
    end_offset: int


class HeadingChunker:
    """
    Split documents by headings, respecting size limits.

    Strategy:
    1. Split document by headings to get natural sections
    2. If a section is too small, merge with next section
    3. If a section is too large, split with overlap
    """

    def __init__(
        self,
        min_tokens: int | None = None,
        max_tokens: int | None = None,
        overlap_tokens: int | None = None,
    ):
        settings = get_settings()
        self.min_tokens = min_tokens or settings.chunk_min_tokens
        self.max_tokens = max_tokens or settings.chunk_max_tokens
        self.overlap_tokens = overlap_tokens or settings.chunk_overlap_tokens
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def chunk(self, doc: ParsedDocument, document_id: str) -> list[Chunk]:
        """
        Split a parsed document into chunks.

        Args:
            doc: Parsed document with text and headings
            document_id: Parent document ID for chunk IDs

        Returns:
            List of Chunk objects
        """
        if not doc.text.strip():
            return []

        # Split into sections by headings
        sections = self._split_by_headings(doc.text, doc.headings)

        # Merge small sections
        merged_sections = self._merge_small_sections(sections)

        # Split large sections and create chunks
        chunks = []
        chunk_index = 0

        for section in merged_sections:
            token_count = self._count_tokens(section.text)

            if token_count <= self.max_tokens:
                # Section fits in one chunk
                chunk = self._create_chunk(
                    document_id=document_id,
                    chunk_index=chunk_index,
                    content=section.text,
                    heading_path=section.heading_path,
                    start_offset=section.start_offset,
                    end_offset=section.end_offset,
                )
                chunks.append(chunk)
                chunk_index += 1
            else:
                # Split large section with overlap
                sub_texts = self._split_with_overlap(section.text)
                for i, sub_text in enumerate(sub_texts):
                    chunk = self._create_chunk(
                        document_id=document_id,
                        chunk_index=chunk_index,
                        content=sub_text,
                        heading_path=f"{section.heading_path} (part {i + 1})" if section.heading_path else None,
                        start_offset=None,  # Precise offsets lost after split
                        end_offset=None,
                    )
                    chunks.append(chunk)
                    chunk_index += 1

        return chunks

    def _split_by_headings(
        self, text: str, headings: list[tuple[int, str, int]]
    ) -> list[Section]:
        """Split text into sections based on headings."""
        if not headings:
            return [
                Section(
                    text=text.strip(),
                    heading_path="",
                    start_offset=0,
                    end_offset=len(text),
                )
            ]

        sections = []
        heading_stack: list[tuple[int, str]] = []  # (level, text)

        # Add positions for splitting
        positions = [(h[2], h[0], h[1]) for h in headings]  # (offset, level, text)
        positions.append((len(text), 0, ""))  # End marker

        prev_pos = 0
        for i, (offset, level, heading_text) in enumerate(positions[:-1]):
            # Get text from previous position to this heading
            if prev_pos < offset:
                section_text = text[prev_pos:offset].strip()
                if section_text:
                    sections.append(
                        Section(
                            text=section_text,
                            heading_path=self._build_heading_path(heading_stack),
                            start_offset=prev_pos,
                            end_offset=offset,
                        )
                    )

            # Update heading stack
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, heading_text))

            prev_pos = offset

        # Handle remaining text after last heading
        if prev_pos < len(text):
            next_pos = positions[-1][0]  # End of text
            section_text = text[prev_pos:next_pos].strip()
            if section_text:
                sections.append(
                    Section(
                        text=section_text,
                        heading_path=self._build_heading_path(heading_stack),
                        start_offset=prev_pos,
                        end_offset=next_pos,
                    )
                )

        return sections

    def _build_heading_path(self, stack: list[tuple[int, str]]) -> str:
        """Build a heading path string from the stack."""
        return " > ".join(h[1] for h in stack)

    def _merge_small_sections(self, sections: list[Section]) -> list[Section]:
        """Merge sections that are too small."""
        if not sections:
            return []

        merged = []
        current = sections[0]

        for next_section in sections[1:]:
            current_tokens = self._count_tokens(current.text)
            next_tokens = self._count_tokens(next_section.text)

            # If current is small and combined would fit, merge
            if current_tokens < self.min_tokens and (current_tokens + next_tokens) <= self.max_tokens:
                current = Section(
                    text=f"{current.text}\n\n{next_section.text}",
                    heading_path=next_section.heading_path or current.heading_path,
                    start_offset=current.start_offset,
                    end_offset=next_section.end_offset,
                )
            else:
                if current.text.strip():
                    merged.append(current)
                current = next_section

        if current.text.strip():
            merged.append(current)

        return merged

    def _split_with_overlap(self, text: str) -> list[str]:
        """Split text into chunks with overlap."""
        tokens = self.tokenizer.encode(text)
        chunks = []
        start = 0

        while start < len(tokens):
            end = min(start + self.max_tokens, len(tokens))

            # Try to find a good split point (sentence boundary)
            if end < len(tokens):
                chunk_text = self.tokenizer.decode(tokens[start:end])
                # Find last sentence boundary
                for sep in [". ", ".\n", "\n\n", "\n"]:
                    last_sep = chunk_text.rfind(sep)
                    if last_sep > len(chunk_text) // 2:
                        end = start + len(self.tokenizer.encode(chunk_text[: last_sep + 1]))
                        break

            chunk_text = self.tokenizer.decode(tokens[start:end])
            chunks.append(chunk_text.strip())

            # Move start with overlap
            start = max(start + 1, end - self.overlap_tokens)

        return chunks

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.tokenizer.encode(text))

    def _create_chunk(
        self,
        document_id: str,
        chunk_index: int,
        content: str,
        heading_path: str | None,
        start_offset: int | None,
        end_offset: int | None,
    ) -> Chunk:
        """Create a Chunk object with computed ID and hash."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        chunk_id = f"{document_id}:{content_hash}"

        return Chunk(
            id=chunk_id,
            document_id=document_id,
            chunk_index=chunk_index,
            content=content,
            content_hash=content_hash,
            heading_path=heading_path,
            start_offset=start_offset,
            end_offset=end_offset,
            token_count=self._count_tokens(content),
        )


# Singleton chunker instance
_chunker = None


def get_chunker() -> HeadingChunker:
    """Get the singleton chunker instance."""
    global _chunker
    if _chunker is None:
        _chunker = HeadingChunker()
    return _chunker

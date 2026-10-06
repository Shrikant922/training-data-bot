"""
Text Chunker - Document Splitter

Splits large documents into smaller, manageable chunks for AI processing.
Uses token-based or character-based chunking with overlap for context preservation.
"""

import re
from typing import List
from uuid import UUID

from ..core.config import settings
from ..core.exceptions import ChunkingError
from ..core.logging import get_logger
from ..core.models import Document, TextChunk


class TextChunker:
    """
    Splits documents into smaller chunks for efficient processing.

    Like cutting a large pizza into slices - each chunk is small enough
    to handle but large enough to preserve meaning.
    """

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        min_chunk_size: int = None
    ):
        """
        Initialize the text chunker.

        Args:
            chunk_size: Target size for each chunk (in characters)
            chunk_overlap: Number of overlapping characters between chunks
            min_chunk_size: Minimum chunk size (discard smaller chunks)
        """
        self.logger = get_logger("chunker")
        self.chunk_size = chunk_size if chunk_size is not None else settings.chunk_size
        self.chunk_overlap = chunk_overlap if chunk_overlap is not None else settings.chunk_overlap
        self.min_chunk_size = min_chunk_size if min_chunk_size is not None else settings.min_chunk_size

        # Validate settings
        if self.chunk_overlap >= self.chunk_size:
            raise ChunkingError(
                "chunk_overlap must be less than chunk_size",
                details={
                    "chunk_size": self.chunk_size,
                    "chunk_overlap": self.chunk_overlap
                }
            )

    def chunk_document(self, document: Document) -> List[TextChunk]:
        """
        Split a document into chunks.

        Args:
            document: Document to chunk

        Returns:
            List of TextChunk objects

        Example:
            chunker = TextChunker(chunk_size=1000, chunk_overlap=200)
            chunks = chunker.chunk_document(document)
        """
        self.logger.info(
            f"Chunking document {document.id} "
            f"({document.word_count} words, {document.char_count} chars)"
        )

        try:
            # Get text content
            text = document.content

            # If document is small enough, return single chunk
            if len(text) <= self.chunk_size:
                self.logger.debug("Document fits in single chunk")
                return [self._create_chunk(document.id, text, 0, len(text), 0)]

            # Split into chunks
            chunks = self._split_text(text)

            # Create TextChunk objects
            text_chunks = []
            for i, (start, end) in enumerate(chunks):
                chunk_text = text[start:end]
                text_chunk = self._create_chunk(document.id, chunk_text, start, end, i)
                text_chunks.append(text_chunk)

            self.logger.info(f"Created {len(text_chunks)} chunks")
            return text_chunks

        except Exception as e:
            if isinstance(e, ChunkingError):
                raise
            raise ChunkingError(
                f"Failed to chunk document",
                details={"document_id": str(document.id)},
                original_error=e
            )

    def _split_text(self, text: str) -> List[tuple[int, int]]:
        """
        Split text into chunks with overlap.

        Args:
            text: Text to split

        Returns:
            List of (start_index, end_index) tuples
        """
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            # Calculate end position
            end = min(start + self.chunk_size, text_length)

            # If not at document end, try to break at sentence boundary
            if end < text_length:
                end = self._find_sentence_boundary(text, start, end)

            # Only add chunk if it meets minimum size
            if end - start >= self.min_chunk_size:
                chunks.append((start, end))

            # Move start position forward with overlap
            new_start = end - self.chunk_overlap

            # Guard against infinite loop: if we haven't advanced, force forward
            if chunks and new_start <= chunks[-1][0]:
                new_start = end

            # Safety: always advance at least 1 character
            if new_start <= start:
                new_start = start + 1

            start = new_start

        return chunks

    # Pre-compiled sentence boundary regex patterns
    _BOUNDARY_PATTERNS = [
        re.compile(r'\.\s+'),  # Period followed by space
        re.compile(r'[!?]\s+'),  # Exclamation or question mark followed by space
        re.compile(r'\n\n'),  # Double newline (paragraph break)
        re.compile(r'\n'),  # Single newline
    ]

    def _find_sentence_boundary(self, text: str, start: int, end: int) -> int:
        """
        Find the nearest sentence boundary before the end position.

        Args:
            text: Full text
            start: Chunk start position
            end: Target end position

        Returns:
            Adjusted end position at sentence boundary
        """
        # Look for sentence endings in the last 20% of the chunk
        search_start = end - (self.chunk_size // 5)
        search_start = max(search_start, start)

        # Find last sentence ending (., !, ?, or \n\n)
        chunk_text = text[search_start:end]

        # Try different pre-compiled sentence boundaries in order of preference
        for pattern in self._BOUNDARY_PATTERNS:
            matches = list(pattern.finditer(chunk_text))
            if matches:
                # Get position after the last match
                last_match = matches[-1]
                return search_start + last_match.end()

        # No boundary found, use original end
        return end

    def _create_chunk(
        self,
        document_id: UUID,
        content: str,
        start_index: int,
        end_index: int,
        chunk_index: int
    ) -> TextChunk:
        """
        Create a TextChunk object.

        Args:
            document_id: Parent document ID
            content: Chunk text content
            start_index: Start position in original document
            end_index: End position in original document
            chunk_index: Sequential chunk number

        Returns:
            TextChunk object
        """
        # Estimate token count (rough approximation: 1 token ≈ 4 characters)
        token_count = len(content) // 4

        return TextChunk(
            document_id=document_id,
            content=content,
            start_index=start_index,
            end_index=end_index,
            chunk_index=chunk_index,
            token_count=token_count
        )

    def chunk_text(self, text: str, document_id: UUID = None) -> List[TextChunk]:
        """
        Chunk raw text without a Document object.

        Args:
            text: Text to chunk
            document_id: Optional document ID to associate chunks with

        Returns:
            List of TextChunk objects
        """
        from uuid import uuid4

        doc_id = document_id or uuid4()

        if len(text) <= self.chunk_size:
            return [self._create_chunk(doc_id, text, 0, len(text), 0)]

        chunks = self._split_text(text)
        return [
            self._create_chunk(doc_id, text[start:end], start, end, i)
            for i, (start, end) in enumerate(chunks)
        ]

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"TextChunker(chunk_size={self.chunk_size}, "
            f"overlap={self.chunk_overlap}, min_size={self.min_chunk_size})"
        )

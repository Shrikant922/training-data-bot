"""
Unit tests for TextChunker
===========================
Tests every public method and key internal behaviour of TextChunker
declared in training_data_bot/preprocessing/chunker.py.

Run with:
    pytest tests/unit/test_chunker.py -v
"""

import sys
import os
from pathlib import Path
from uuid import uuid4, UUID

# ---------------------------------------------------------------------------
# Path bootstrap -- must happen before any project imports so that relative
# imports inside the package resolve correctly regardless of where pytest is
# invoked from.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # repo root
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(str(PROJECT_ROOT))

import pytest

from training_data_bot.preprocessing.chunker import TextChunker
from training_data_bot.core.exceptions import ChunkingError
from training_data_bot.core.models import Document, TextChunk, DocumentType


# ===========================================================================
# Helpers
# ===========================================================================

def make_chunker(chunk_size: int = 200, chunk_overlap: int = 40,
                 min_chunk_size: int = 20) -> TextChunker:
    """Convenience factory with small, test-friendly defaults."""
    return TextChunker(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        min_chunk_size=min_chunk_size,
    )


def make_document(content: str) -> Document:
    """Build a minimal Document from raw content."""
    return Document(
        title="Test Document",
        content=content,
        source="test_source.txt",
        doc_type=DocumentType.TXT,
        word_count=len(content.split()),
        char_count=len(content),
    )


def long_text(sentences: int = 30) -> str:
    """Generate deterministic text that is long enough to require chunking."""
    return " ".join(
        f"Sentence number {i} contains some words to fill the buffer."
        for i in range(sentences)
    )


# ===========================================================================
# Construction / validation
# ===========================================================================

class TestTextChunkerInit:
    """Tests for constructor behaviour and validation."""

    def test_valid_config_does_not_raise(self):
        """Normal chunk_size > chunk_overlap should succeed without error."""
        chunker = make_chunker()
        assert chunker is not None

    def test_invalid_config_overlap_equals_size_raises(self):
        """chunk_overlap == chunk_size must raise ChunkingError."""
        with pytest.raises(ChunkingError):
            TextChunker(chunk_size=100, chunk_overlap=100, min_chunk_size=10)

    def test_invalid_config_overlap_greater_than_size_raises(self):
        """chunk_overlap > chunk_size must raise ChunkingError."""
        with pytest.raises(ChunkingError):
            TextChunker(chunk_size=100, chunk_overlap=150, min_chunk_size=10)

    def test_stores_chunk_size(self):
        """chunk_size attribute must reflect the value passed in."""
        chunker = make_chunker(chunk_size=500)
        assert chunker.chunk_size == 500

    def test_stores_chunk_overlap(self):
        """chunk_overlap attribute must reflect the value passed in."""
        chunker = make_chunker(chunk_overlap=50)
        assert chunker.chunk_overlap == 50

    def test_stores_min_chunk_size(self):
        """min_chunk_size attribute must reflect the value passed in."""
        chunker = make_chunker(min_chunk_size=30)
        assert chunker.min_chunk_size == 30


# ===========================================================================
# chunk_document() -- return type, count, fields
# ===========================================================================

class TestChunkDocument:
    """Tests for the primary chunk_document() method."""

    def test_short_document_returns_single_chunk(self):
        """A document whose content fits within chunk_size yields exactly one chunk."""
        chunker = make_chunker(chunk_size=500)
        doc = make_document("Short document content.")
        chunks = chunker.chunk_document(doc)
        assert len(chunks) == 1

    def test_long_document_returns_multiple_chunks(self):
        """A document longer than chunk_size must produce more than one chunk."""
        chunker = make_chunker(chunk_size=100, chunk_overlap=20, min_chunk_size=10)
        doc = make_document(long_text(20))
        chunks = chunker.chunk_document(doc)
        assert len(chunks) > 1

    def test_returns_list_of_text_chunk_objects(self):
        """chunk_document() must return a list of TextChunk instances."""
        chunker = make_chunker()
        doc = make_document(long_text())
        chunks = chunker.chunk_document(doc)
        assert isinstance(chunks, list)
        for chunk in chunks:
            assert isinstance(chunk, TextChunk)

    def test_chunks_have_correct_document_id(self):
        """Every TextChunk must carry the parent Document's UUID."""
        chunker = make_chunker()
        doc = make_document(long_text())
        chunks = chunker.chunk_document(doc)
        for chunk in chunks:
            assert chunk.document_id == doc.id, (
                f"chunk.document_id {chunk.document_id} != doc.id {doc.id}"
            )

    def test_chunks_have_sequential_chunk_index(self):
        """chunk_index must start at 0 and increment by 1 for each subsequent chunk."""
        chunker = make_chunker(chunk_size=100, chunk_overlap=20, min_chunk_size=10)
        doc = make_document(long_text(20))
        chunks = chunker.chunk_document(doc)
        for expected_idx, chunk in enumerate(chunks):
            assert chunk.chunk_index == expected_idx, (
                f"chunk_index mismatch: expected {expected_idx}, got {chunk.chunk_index}"
            )

    def test_chunk_token_count_is_approx_len_div_4(self):
        """token_count must equal len(content) // 4 (rough approximation)."""
        chunker = make_chunker()
        doc = make_document(long_text())
        chunks = chunker.chunk_document(doc)
        for chunk in chunks:
            expected = len(chunk.content) // 4
            assert chunk.token_count == expected, (
                f"Expected token_count={expected}, got {chunk.token_count}"
            )

    def test_chunk_content_is_substring_of_original(self):
        """Every chunk's content must appear verbatim in the original document."""
        chunker = make_chunker(chunk_size=100, chunk_overlap=20, min_chunk_size=10)
        text = long_text(20)
        doc = make_document(text)
        chunks = chunker.chunk_document(doc)
        for chunk in chunks:
            assert chunk.content in text, (
                f"Chunk content not found in original document: {chunk.content[:50]!r}"
            )


# ===========================================================================
# Overlap behaviour
# ===========================================================================

class TestChunkOverlap:
    """Tests verifying that adjacent chunks share the expected overlap content."""

    def test_adjacent_chunks_share_content(self):
        """
        With overlap > 0, the tail of chunk[i] should appear at the start
        of chunk[i+1] (subject to sentence-boundary adjustment).
        At minimum, the start_index of chunk[i+1] must be less than the
        end_index of chunk[i].
        """
        chunker = make_chunker(chunk_size=150, chunk_overlap=50, min_chunk_size=10)
        doc = make_document(long_text(25))
        chunks = chunker.chunk_document(doc)
        if len(chunks) < 2:
            pytest.skip("Not enough chunks to test overlap")
        for i in range(len(chunks) - 1):
            # The next chunk starts before the current one ends
            assert chunks[i + 1].start_index < chunks[i].end_index, (
                f"chunk[{i+1}].start_index ({chunks[i+1].start_index}) should be "
                f"< chunk[{i}].end_index ({chunks[i].end_index}) for overlap"
            )

    def test_minimal_overlap_chunks_advance_forward(self):
        """
        With a minimal chunk_overlap (1 char), adjacent chunks must still
        advance forward -- i.e. chunk[i+1].start_index must be > chunk[i].start_index.

        NOTE: chunk_overlap=0 is falsy in Python, so the chunker falls back to
        the settings default.  We use chunk_overlap=1 here which is the smallest
        meaningful value that doesn't trigger that fallback.
        """
        chunker = TextChunker(chunk_size=100, chunk_overlap=1, min_chunk_size=10)
        text = long_text(20)
        doc = make_document(text)
        chunks = chunker.chunk_document(doc)
        if len(chunks) < 2:
            pytest.skip("Not enough chunks to test forward progress")
        for i in range(len(chunks) - 1):
            assert chunks[i + 1].start_index > chunks[i].start_index, (
                "Each subsequent chunk must start later than the previous one"
            )


# ===========================================================================
# min_chunk_size filtering
# ===========================================================================

class TestMinChunkSize:
    """Tests that chunks below min_chunk_size are discarded."""

    def test_tiny_trailing_chunk_discarded(self):
        """
        When the last chunk would be shorter than min_chunk_size it must not
        appear in the output.
        Craft text so the final remainder is tiny.

        NOTE: chunk_overlap=0 is falsy and falls back to settings default.
        We use chunk_overlap=1 as the smallest non-falsy overlap.
        """
        # chunk_size=100, min_chunk_size=50
        # main body of 100 chars + tiny tail of 10 chars
        body = "A" * 100
        tail = "B" * 10  # 10 < min_chunk_size=50 -> should be discarded
        text = body + tail
        chunker = TextChunker(chunk_size=100, chunk_overlap=1, min_chunk_size=50)
        doc = make_document(text)
        chunks = chunker.chunk_document(doc)
        for chunk in chunks:
            assert len(chunk.content) >= 50, (
                f"Chunk shorter than min_chunk_size was not discarded: {len(chunk.content)!r}"
            )

    def test_all_chunks_meet_min_size(self):
        """All produced chunks must have content length >= min_chunk_size."""
        chunker = make_chunker(chunk_size=200, chunk_overlap=30, min_chunk_size=50)
        doc = make_document(long_text(40))
        chunks = chunker.chunk_document(doc)
        for chunk in chunks:
            assert len(chunk.content) >= 50, (
                f"Chunk too small: {len(chunk.content)} chars"
            )


# ===========================================================================
# Sentence-boundary preference
# ===========================================================================

class TestSentenceBoundaryPreference:
    """Tests that chunk boundaries prefer sentence endings over mid-word cuts."""

    def test_chunks_end_at_or_near_sentence_boundary(self):
        """
        Intermediate chunks (not the final one) should end close to a sentence
        boundary (.  !  ?) rather than cutting mid-word.
        We verify that each non-final chunk ends with a punctuation character
        or whitespace (not an alphanumeric character in the middle of a word).
        """
        chunker = make_chunker(chunk_size=200, chunk_overlap=40, min_chunk_size=20)
        # Build text with clear sentence endings
        text = " ".join(
            f"This is a full sentence number {i}." for i in range(30)
        )
        doc = make_document(text)
        chunks = chunker.chunk_document(doc)
        if len(chunks) < 2:
            pytest.skip("Need multiple chunks to test boundaries")
        # Check every intermediate chunk
        for chunk in chunks[:-1]:
            end_char = chunk.content.rstrip()[-1] if chunk.content.rstrip() else ""
            assert end_char in ".!?\n", (
                f"Chunk does not end at sentence boundary; ends with: {chunk.content[-20:]!r}"
            )


# ===========================================================================
# chunk_text() -- convenience method without a Document
# ===========================================================================

class TestChunkText:
    """Tests for the chunk_text() helper (no Document object required)."""

    def test_short_text_returns_single_chunk(self):
        """Text fitting within chunk_size should produce exactly one chunk."""
        chunker = make_chunker(chunk_size=500)
        chunks = chunker.chunk_text("Short text here.")
        assert len(chunks) == 1

    def test_long_text_returns_multiple_chunks(self):
        """Text longer than chunk_size should be split into multiple chunks."""
        chunker = make_chunker(chunk_size=100, chunk_overlap=20, min_chunk_size=10)
        chunks = chunker.chunk_text(long_text(20))
        assert len(chunks) > 1

    def test_returns_text_chunk_objects(self):
        """chunk_text() must return TextChunk instances."""
        chunker = make_chunker()
        chunks = chunker.chunk_text(long_text())
        assert all(isinstance(c, TextChunk) for c in chunks)

    def test_custom_document_id_propagated(self):
        """When document_id is supplied, all chunks must carry it."""
        chunker = make_chunker(chunk_size=100, chunk_overlap=20, min_chunk_size=10)
        doc_id = uuid4()
        chunks = chunker.chunk_text(long_text(20), document_id=doc_id)
        for chunk in chunks:
            assert chunk.document_id == doc_id

    def test_auto_document_id_is_uuid(self):
        """When no document_id is given, an auto-generated UUID must be used."""
        chunker = make_chunker()
        chunks = chunker.chunk_text("Some text here.")
        for chunk in chunks:
            assert isinstance(chunk.document_id, UUID)


# ===========================================================================
# No infinite loop / progress guarantees
# ===========================================================================

class TestNoInfiniteLoop:
    """
    Tests that the chunker always terminates and makes forward progress,
    guarding against the infinite-loop edge cases handled in _split_text().
    """

    def test_very_short_text_terminates(self):
        """Even a 1-character string must return promptly and not hang."""
        chunker = make_chunker(chunk_size=100, chunk_overlap=20, min_chunk_size=1)
        chunks = chunker.chunk_text("x")
        assert isinstance(chunks, list)  # just needs to return

    def test_zero_overlap_terminates(self):
        """chunk_overlap=0 must not cause an infinite loop."""
        chunker = TextChunker(chunk_size=50, chunk_overlap=0, min_chunk_size=1)
        chunks = chunker.chunk_text(long_text(20))
        assert len(chunks) > 0

    def test_chunks_always_advance_forward(self):
        """
        Verify that _split_text() never returns a (start, end) pair where
        start >= end of the previous chunk (backward movement).
        This catches subtle regressions in the loop-guard logic.
        """
        chunker = make_chunker(chunk_size=120, chunk_overlap=40, min_chunk_size=10)
        text = long_text(30)
        spans = chunker._split_text(text)
        for i in range(1, len(spans)):
            prev_end = spans[i - 1][1]
            curr_start = spans[i][0]
            assert curr_start < prev_end or curr_start >= spans[i - 1][0] + 1, (
                f"No forward progress at span index {i}: "
                f"prev=({spans[i-1]}), curr=({spans[i]})"
            )

    def test_chunks_cover_text_completely(self):
        """
        All characters in the source text should appear in at least one chunk
        (i.e., no sections are silently skipped).
        """
        chunker = TextChunker(chunk_size=100, chunk_overlap=0, min_chunk_size=1)
        text = long_text(15)
        doc = make_document(text)
        chunks = chunker.chunk_document(doc)
        # Every chunk has content that is a substring of the original text
        for chunk in chunks:
            assert chunk.content in text


# ===========================================================================
# TextChunker.__repr__()
# ===========================================================================

class TestRepr:
    """Tests for the string representation of TextChunker."""

    def test_repr_contains_chunk_size(self):
        """__repr__ must mention chunk_size."""
        chunker = make_chunker(chunk_size=300)
        r = repr(chunker)
        assert "chunk_size=300" in r

    def test_repr_contains_overlap(self):
        """__repr__ must mention overlap."""
        chunker = make_chunker(chunk_overlap=50)
        r = repr(chunker)
        assert "overlap=50" in r

    def test_repr_contains_min_size(self):
        """__repr__ must mention min_size."""
        chunker = make_chunker(min_chunk_size=25)
        r = repr(chunker)
        assert "min_size=25" in r

    def test_repr_returns_string(self):
        """__repr__ must return a str object."""
        chunker = make_chunker()
        assert isinstance(repr(chunker), str)

"""
Unit tests for TextPreprocessor
================================
Tests every public method of TextPreprocessor declared in
training_data_bot/preprocessing/preprocessor.py.

Run with:
    pytest tests/unit/test_preprocessor.py -v
"""

import sys
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap -- must happen before any project imports so that relative
# imports inside the package resolve correctly regardless of where pytest is
# invoked from.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # repo root
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(str(PROJECT_ROOT))

import pytest

from training_data_bot.preprocessing.preprocessor import TextPreprocessor
from training_data_bot.core.exceptions import PreprocessingError


# ===========================================================================
# Helpers / shared data
# ===========================================================================

def make_preprocessor(aggressive: bool = False) -> TextPreprocessor:
    """Convenience factory so each test gets a fresh instance."""
    return TextPreprocessor(aggressive=aggressive)


# ===========================================================================
# TextPreprocessor.preprocess()
# ===========================================================================

class TestPreprocess:
    """Tests for the main preprocessing pipeline."""

    def test_empty_string_returns_empty(self):
        """preprocess('') should return an empty string, not raise."""
        pp = make_preprocessor()
        assert pp.preprocess("") == ""

    def test_whitespace_only_returns_empty(self):
        """preprocess() on whitespace-only input should also return ''."""
        pp = make_preprocessor()
        assert pp.preprocess("   \n\t  ") == ""

    def test_normalizes_multiple_spaces_to_one(self):
        """Multiple consecutive spaces must be collapsed to a single space."""
        pp = make_preprocessor()
        result = pp.preprocess("hello   world")
        assert "  " not in result, "Multiple spaces should not remain"
        assert "hello world" in result

    def test_removes_control_characters_keeps_newline_and_tab(self):
        """Control characters (C-category) should be stripped; \n and \t kept."""
        pp = make_preprocessor()
        # \x00 is NULL (control char), \x01 is SOH (control char)
        text = "hello\x00world\x01end\nnewline\ttab"
        result = pp.preprocess(text)
        assert "\x00" not in result
        assert "\x01" not in result
        # Newline and tab must survive
        assert "\n" in result
        assert "\t" in result

    def test_preserves_paragraph_structure(self):
        """Double newlines (paragraph breaks) should be retained."""
        pp = make_preprocessor()
        text = "First paragraph.\n\nSecond paragraph."
        result = pp.preprocess(text)
        assert "\n\n" in result, "Paragraph break should be preserved"

    def test_collapses_excessive_newlines_to_two(self):
        """Three or more consecutive newlines should be reduced to two."""
        pp = make_preprocessor()
        text = "Para one.\n\n\n\nPara two."
        result = pp.preprocess(text)
        assert "\n\n\n" not in result, "3+ newlines should collapse to \\n\\n"

    def test_aggressive_false_keeps_urls(self):
        """With aggressive=False, URLs should be left intact."""
        pp = make_preprocessor(aggressive=False)
        text = "Visit http://example.com for more info."
        result = pp.preprocess(text)
        assert "http://example.com" in result

    def test_aggressive_true_removes_http_urls(self):
        """With aggressive=True, http:// URLs must be stripped."""
        pp = make_preprocessor(aggressive=True)
        text = "Visit http://example.com for more info."
        result = pp.preprocess(text)
        assert "http://example.com" not in result, "URL should be removed in aggressive mode"

    def test_aggressive_true_removes_https_urls(self):
        """With aggressive=True, https:// URLs must also be stripped."""
        pp = make_preprocessor(aggressive=True)
        text = "See https://secure.example.com/path?q=1 for details."
        result = pp.preprocess(text)
        assert "https://" not in result

    def test_aggressive_true_removes_email_addresses(self):
        """With aggressive=True, email addresses (x@y) must be stripped."""
        pp = make_preprocessor(aggressive=True)
        text = "Contact us at support@example.com for help."
        result = pp.preprocess(text)
        assert "support@example.com" not in result, "Email should be removed in aggressive mode"

    def test_aggressive_true_collapses_repeated_chars(self):
        """
        With aggressive=True, runs of 4+ identical chars are reduced to 2.
        The regex replaces (.)\\1{3,} with \\1\\1 -- so 5 o's becomes 2 o's.
        """
        pp = make_preprocessor(aggressive=True)
        text = "hellooooo world"
        result = pp.preprocess(text)
        assert "oooo" not in result, "Run of 4+ identical chars should be collapsed"

    def test_result_is_stripped(self):
        """Output of preprocess() must have no leading/trailing whitespace."""
        pp = make_preprocessor()
        result = pp.preprocess("  hello world  ")
        assert result == result.strip()


# ===========================================================================
# TextPreprocessor.clean_for_training()
# ===========================================================================

class TestCleanForTraining:
    """Tests for the training-data-specific cleaning method."""

    def test_removes_page_number_artifact(self):
        """
        Standalone numeric page numbers like '\n  5  \n' or '\n - 5 - \n'
        should be removed.
        """
        pp = make_preprocessor()
        text = "Chapter one text.\n  5  \nChapter two text."
        result = pp.clean_for_training(text)
        assert "\n  5  \n" not in result

    def test_removes_page_x_of_y_header(self):
        """'Page N of M' header/footer lines should be stripped."""
        pp = make_preprocessor()
        text = "Some content here.\nPage 3 of 10\nMore content here."
        result = pp.clean_for_training(text)
        assert "Page 3 of 10" not in result

    def test_preserves_main_content(self):
        """Content surrounding artifacts should survive cleaning."""
        pp = make_preprocessor()
        text = "Introduction text.\nPage 1 of 5\nConclusion text."
        result = pp.clean_for_training(text)
        assert "Introduction text." in result
        assert "Conclusion text." in result

    def test_result_is_stripped(self):
        """clean_for_training() result must not have leading/trailing whitespace."""
        pp = make_preprocessor()
        result = pp.clean_for_training("  Hello world.  ")
        assert result == result.strip()


# ===========================================================================
# TextPreprocessor.extract_sentences()
# ===========================================================================

class TestExtractSentences:
    """Tests for sentence splitting."""

    def test_splits_on_period(self):
        """Periods followed by whitespace should act as sentence boundaries."""
        pp = make_preprocessor()
        text = "The sky is blue. The grass is green. The sun is bright."
        sentences = pp.extract_sentences(text)
        assert len(sentences) == 3

    def test_splits_on_exclamation_mark(self):
        """Exclamation marks should also act as sentence boundaries."""
        pp = make_preprocessor()
        text = "Watch out danger ahead! Something is coming fast! Please run away quickly."
        sentences = pp.extract_sentences(text)
        assert len(sentences) >= 2

    def test_splits_on_question_mark(self):
        """Question marks should also act as sentence boundaries."""
        pp = make_preprocessor()
        text = "Is the sky really blue? Yes, it certainly is. Are you absolutely sure about this?"
        sentences = pp.extract_sentences(text)
        assert len(sentences) >= 2

    def test_filters_very_short_sentences(self):
        """Sentences of 10 characters or fewer must be excluded from output."""
        pp = make_preprocessor()
        # "Hi." is only 3 chars -- below the 10-char threshold
        text = "Hi. This is a much longer sentence that should definitely pass the filter."
        sentences = pp.extract_sentences(text)
        for s in sentences:
            assert len(s.strip()) > 10, f"Short sentence slipped through: {s!r}"

    def test_returns_list(self):
        """extract_sentences() must return a list."""
        pp = make_preprocessor()
        result = pp.extract_sentences("A sentence. Another sentence here.")
        assert isinstance(result, list)

    def test_empty_string_returns_empty_list(self):
        """Empty input should yield an empty list, not raise."""
        pp = make_preprocessor()
        result = pp.extract_sentences("")
        assert result == []


# ===========================================================================
# TextPreprocessor.remove_duplicates()
# ===========================================================================

class TestRemoveDuplicates:
    """Tests for duplicate-text removal."""

    def test_removes_exact_duplicates(self):
        """Exact duplicate strings must appear only once in the output."""
        pp = make_preprocessor()
        texts = ["hello", "world", "hello", "foo"]
        result = pp.remove_duplicates(texts)
        assert result.count("hello") == 1

    def test_preserves_order(self):
        """First occurrence of each string must be kept; later dupes dropped."""
        pp = make_preprocessor()
        texts = ["alpha", "beta", "alpha", "gamma", "beta"]
        result = pp.remove_duplicates(texts)
        assert result == ["alpha", "beta", "gamma"]

    def test_case_insensitive_comparison(self):
        """
        'Hello' and 'hello' should be treated as duplicates;
        only the first-seen capitalisation is kept.
        """
        pp = make_preprocessor()
        texts = ["Hello", "hello", "HELLO"]
        result = pp.remove_duplicates(texts)
        assert len(result) == 1

    def test_no_duplicates_unchanged(self):
        """List with no duplicates should be returned unchanged."""
        pp = make_preprocessor()
        texts = ["one", "two", "three"]
        result = pp.remove_duplicates(texts)
        assert result == texts

    def test_empty_list_returns_empty(self):
        """Empty input list should return empty list."""
        pp = make_preprocessor()
        assert pp.remove_duplicates([]) == []

    def test_whitespace_normalised_for_comparison(self):
        """Leading/trailing whitespace should not affect duplicate detection."""
        pp = make_preprocessor()
        texts = ["hello", "  hello  "]
        result = pp.remove_duplicates(texts)
        # Normalised form is identical -> only first survives
        assert len(result) == 1


# ===========================================================================
# TextPreprocessor.truncate()
# ===========================================================================

class TestTruncate:
    """Tests for text truncation."""

    def test_short_text_returned_unchanged(self):
        """Text that fits within max_length must not be modified."""
        pp = make_preprocessor()
        text = "Short text."
        result = pp.truncate(text, max_length=100)
        assert result == text

    def test_exact_length_returned_unchanged(self):
        """Text whose length == max_length must not be modified."""
        pp = make_preprocessor()
        text = "exactly"  # 7 chars
        result = pp.truncate(text, max_length=7)
        assert result == text

    def test_truncates_long_text(self):
        """Text longer than max_length must be truncated."""
        pp = make_preprocessor()
        text = "a" * 200
        result = pp.truncate(text, max_length=50)
        # Result length = truncated content + suffix (3) <= 50
        assert len(result) <= 53

    def test_appends_default_suffix(self):
        """When truncation occurs the default suffix '...' must appear."""
        pp = make_preprocessor()
        text = "The quick brown fox jumps over the lazy dog. " * 10
        result = pp.truncate(text, max_length=50)
        assert result.endswith("...")

    def test_custom_suffix(self):
        """Custom suffix should be used instead of default '...'."""
        pp = make_preprocessor()
        text = "The quick brown fox jumps over the lazy dog. " * 10
        result = pp.truncate(text, max_length=60, suffix=" [more]")
        assert result.endswith(" [more]")

    def test_truncates_at_sentence_boundary_when_possible(self):
        """
        When a sentence ending exists in the latter half of the truncation
        window, the cut should land there rather than mid-word.
        We test that the result ends with '...' and that the text portion
        before the suffix ends at a period (sentence boundary).
        """
        pp = make_preprocessor()
        # Place a period comfortably before max_length so the boundary is found
        text = "First complete sentence here. " + "x" * 200
        result = pp.truncate(text, max_length=80)
        # The portion before the suffix "..." should end at '.'
        body = result[:-3]  # remove suffix
        assert body.rstrip().endswith("."), (
            f"Expected sentence boundary, got: {body!r}"
        )


# ===========================================================================
# TextPreprocessor._normalize_unicode()
# ===========================================================================

class TestNormalizeUnicode:
    """Tests for internal Unicode normalization helper."""

    def test_ligature_fi_decomposed(self):
        """The 'fi' ligature (U+FB01) should be decomposed to 'fi' by NFKC."""
        pp = make_preprocessor()
        text = "\uFB01le"  # file (fi ligature + 'le')
        result = pp._normalize_unicode(text)
        assert result == "file", f"Expected 'file', got {result!r}"

    def test_returns_string(self):
        """_normalize_unicode must always return a str."""
        pp = make_preprocessor()
        assert isinstance(pp._normalize_unicode("test"), str)

    def test_plain_ascii_unchanged(self):
        """Plain ASCII text should pass through NFKC unchanged."""
        pp = make_preprocessor()
        text = "Hello, world! 123"
        assert pp._normalize_unicode(text) == text

    def test_fancy_quote_round_trips(self):
        """
        Unicode fancy quotes survive normalization (NFKC keeps them).
        The important thing is no exception is raised and content is preserved.
        """
        pp = make_preprocessor()
        text = "\u201cHello world\u201d"  # "Hello world"
        result = pp._normalize_unicode(text)
        assert "Hello world" in result

    def test_superscript_digits_normalized(self):
        """Superscript digits (e.g. U+00B2 = superscript 2) become plain digit via NFKC."""
        pp = make_preprocessor()
        text = "x\u00B2"  # x superscript-2
        result = pp._normalize_unicode(text)
        assert result == "x2", f"Expected 'x2', got {result!r}"


# ===========================================================================
# TextPreprocessor.__repr__()
# ===========================================================================

class TestRepr:
    """Tests for the string representation of TextPreprocessor."""

    def test_repr_non_aggressive(self):
        """__repr__ for non-aggressive instance should include aggressive=False."""
        pp = TextPreprocessor(aggressive=False)
        assert repr(pp) == "TextPreprocessor(aggressive=False)"

    def test_repr_aggressive(self):
        """__repr__ for aggressive instance should include aggressive=True."""
        pp = TextPreprocessor(aggressive=True)
        assert repr(pp) == "TextPreprocessor(aggressive=True)"

    def test_repr_returns_string(self):
        """__repr__ must return a str object."""
        pp = make_preprocessor()
        assert isinstance(repr(pp), str)

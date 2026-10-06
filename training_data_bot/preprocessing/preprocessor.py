"""
Text Preprocessor - Text Cleaning and Normalization

Handles text cleaning, normalization, and preprocessing before chunking or AI processing.
"""

import re
import unicodedata
from typing import Optional

from ..core.config import settings
from ..core.exceptions import PreprocessingError
from ..core.logging import get_logger


class TextPreprocessor:
    """
    Preprocesses and cleans text content for training data generation.

    Handles:
    - Whitespace normalization
    - Unicode normalization
    - Special character handling
    - Encoding fixes
    - Optional aggressive cleaning
    """

    # Pre-compiled regular expressions for maximum speed
    _RE_SPACES = re.compile(r' +')
    _RE_NEWLINES = re.compile(r'\n{3,}')
    _RE_LINE_SPACES = re.compile(r' *\n *')
    _RE_ALL_WHITESPACE = re.compile(r'\s+')
    _RE_URL = re.compile(r'https?://\S+|www\.\S+')
    _RE_EMAIL = re.compile(r'\S+@\S+')
    _RE_EXCESSIVE_PUNCT = re.compile(r'[!?\.]{3,}')
    _RE_REPEATED_CHARS = re.compile(r'(.)\1{3,}')
    _RE_PAGE_NUMBERS = re.compile(r'\n\s*[-—]?\s*\d+\s*[-—]?\s*\n')
    _RE_PAGE_HEADERS = re.compile(r'\n\s*Page \d+ of \d+\s*\n')
    _RE_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+')

    def __init__(self, aggressive: bool = False):
        """
        Initialize the text preprocessor.

        Args:
            aggressive: Use aggressive cleaning (removes more content)
        """
        self.logger = get_logger("preprocessor")
        self.aggressive = aggressive

    def preprocess(self, text: str, preserve_structure: bool = True) -> str:
        """
        Main preprocessing pipeline.

        Args:
            text: Raw text to preprocess
            preserve_structure: Keep paragraph breaks and structure

        Returns:
            Cleaned and normalized text

        Example:
            preprocessor = TextPreprocessor()
            clean_text = preprocessor.preprocess(raw_text)
        """
        if not text or not text.strip():
            return ""

        try:
            # Pipeline stages
            text = self._normalize_unicode(text)
            text = self._fix_encoding_issues(text)
            text = self._normalize_whitespace(text, preserve_structure)
            text = self._remove_control_characters(text)

            if self.aggressive:
                text = self._aggressive_clean(text)

            return text.strip()

        except Exception as e:
            raise PreprocessingError(
                "Text preprocessing failed",
                original_error=e
            )

    def _normalize_unicode(self, text: str) -> str:
        """
        Normalize Unicode characters to standard form.

        Args:
            text: Input text

        Returns:
            Unicode-normalized text
        """
        # Use NFKC normalization (compatibility decomposition + canonical composition)
        # This handles things like fancy quotes, ligatures, etc.
        return unicodedata.normalize('NFKC', text)

    def _fix_encoding_issues(self, text: str) -> str:
        """
        Fix common encoding issues.

        Args:
            text: Input text

        Returns:
            Text with encoding issues fixed
        """
        # Common encoding fixes
        replacements = {
            'â€™': "'",  # Smart single quote
            'â€œ': '"',  # Smart double quote open
            'â€': '"',   # Smart double quote close
            'â€"': '—',  # Em dash
            'â€"': '–',  # En dash
            'Ã©': 'é',   # Common Latin-1 issue
            'Ã¡': 'á',
            'Ã³': 'ó',
        }

        for wrong, right in replacements.items():
            text = text.replace(wrong, right)

        return text

    def _normalize_whitespace(self, text: str, preserve_structure: bool) -> str:
        """
        Normalize whitespace characters.

        Args:
            text: Input text
            preserve_structure: Keep paragraph breaks

        Returns:
            Text with normalized whitespace
        """
        if preserve_structure:
            # Replace multiple spaces with single space
            text = self._RE_SPACES.sub(' ', text)

            # Normalize line breaks (keep paragraph structure)
            text = self._RE_NEWLINES.sub('\n\n', text)  # Max 2 consecutive newlines

            # Remove spaces at start/end of lines
            text = self._RE_LINE_SPACES.sub('\n', text)

        else:
            # Aggressive: replace all whitespace with single space
            text = self._RE_ALL_WHITESPACE.sub(' ', text)

        return text

    def _remove_control_characters(self, text: str) -> str:
        """
        Remove control characters (except newlines and tabs).

        Args:
            text: Input text

        Returns:
            Text with control characters removed
        """
        # Keep newlines, tabs, and printable characters
        return ''.join(
            char for char in text
            if char in '\n\t' or not unicodedata.category(char).startswith('C')
        )

    def _aggressive_clean(self, text: str) -> str:
        """
        Aggressive cleaning for very noisy text.

        Args:
            text: Input text

        Returns:
            Aggressively cleaned text
        """
        # Remove URLs
        text = self._RE_URL.sub('', text)

        # Remove email addresses
        text = self._RE_EMAIL.sub('', text)

        # Remove excessive punctuation
        text = self._RE_EXCESSIVE_PUNCT.sub('.', text)

        # Remove repeated characters (e.g., "hellooooo" -> "hello")
        text = self._RE_REPEATED_CHARS.sub(r'\1\1', text)

        # Clean up whitespace again
        text = self._RE_ALL_WHITESPACE.sub(' ', text)

        return text

    def clean_for_training(self, text: str) -> str:
        """
        Special preprocessing for training data generation.

        More conservative - preserves information needed for Q&A, etc.

        Args:
            text: Input text

        Returns:
            Training-ready text
        """
        text = self._normalize_unicode(text)
        text = self._fix_encoding_issues(text)
        text = self._normalize_whitespace(text, preserve_structure=True)
        text = self._remove_control_characters(text)

        # Remove obvious artifacts but keep content
        # Remove page numbers (e.g., "Page 1", "- 5 -")
        text = self._RE_PAGE_NUMBERS.sub('\n', text)

        # Remove common headers/footers
        text = self._RE_PAGE_HEADERS.sub('\n', text)

        return text.strip()

    def extract_sentences(self, text: str) -> list[str]:
        """
        Split text into sentences.

        Args:
            text: Input text

        Returns:
            List of sentences

        Example:
            sentences = preprocessor.extract_sentences(text)
        """
        # Simple sentence splitting (can be improved with spaCy/nltk)
        # Split on sentence endings followed by space or newline
        sentences = self._RE_SENTENCE_SPLIT.split(text)

        # Filter out empty strings and very short sentences
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        return sentences

    def remove_duplicates(self, texts: list[str]) -> list[str]:
        """
        Remove duplicate texts while preserving order.

        Args:
            texts: List of text strings

        Returns:
            Deduplicated list

        Example:
            unique_texts = preprocessor.remove_duplicates(text_list)
        """
        seen = set()
        unique = []

        for text in texts:
            # Normalize for comparison
            normalized = text.lower().strip()

            if normalized not in seen:
                seen.add(normalized)
                unique.append(text)

        removed_count = len(texts) - len(unique)
        if removed_count > 0:
            self.logger.info(f"Removed {removed_count} duplicate texts")

        return unique

    def truncate(self, text: str, max_length: int, suffix: str = "...") -> str:
        """
        Truncate text to maximum length.

        Args:
            text: Input text
            max_length: Maximum character count
            suffix: String to append when truncated

        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text

        # Try to truncate at sentence boundary
        truncated = text[:max_length - len(suffix)]

        # Find last sentence ending
        last_period = truncated.rfind('.')
        last_exclaim = truncated.rfind('!')
        last_question = truncated.rfind('?')

        boundary = max(last_period, last_exclaim, last_question)

        if boundary > max_length // 2:  # Only if we found a good boundary
            truncated = truncated[:boundary + 1]
        else:
            # No good boundary, truncate at space
            last_space = truncated.rfind(' ')
            if last_space > 0:
                truncated = truncated[:last_space]

        return truncated + suffix

    def __repr__(self) -> str:
        """String representation."""
        return f"TextPreprocessor(aggressive={self.aggressive})"

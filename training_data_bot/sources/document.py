"""
Document Loader - Text Format Specialist

Handles loading of text-based document formats:
- Plain text (.txt)
- Markdown (.md)
- HTML (.html)
- JSON (.json)
- CSV (.csv)
- Word documents (.docx)
"""

import asyncio
import csv
import json
from pathlib import Path
from typing import Union

import aiofiles
from bs4 import BeautifulSoup
from docx import Document as DocxDocument

from ..core.exceptions import DocumentLoadError, DocumentParseError
from ..core.models import DocumentType
from .base import BaseLoader


class DocumentLoader(BaseLoader):
    """
    Loader for text-based document formats.

    Supports: TXT, MD, HTML, JSON, CSV, DOCX
    """

    def __init__(self):
        super().__init__()
        self.supported_formats = [
            DocumentType.TXT,
            DocumentType.MD,
            DocumentType.HTML,
            DocumentType.JSON,
            DocumentType.CSV,
            DocumentType.DOCX,
        ]

    async def load_single(self, source: Union[str, Path], encoding: str = "utf-8", **kwargs) -> "Document":
        """
        Load a single text-based document.

        Args:
            source: Path to the document
            encoding: Text encoding (default: utf-8)
            **kwargs: Additional options

        Returns:
            Document object with extracted content
        """
        source_path = Path(source)
        self.validate_file_exists(source_path)

        doc_type = self.get_document_type(source_path)

        if doc_type not in self.supported_formats:
            raise DocumentLoadError(
                f"Unsupported format for DocumentLoader: {doc_type}",
                details={"source": str(source), "type": doc_type.value}
            )

        self.logger.info(f"Loading {doc_type.value} document: {source_path.name}")

        try:
            # Route to appropriate loader
            if doc_type == DocumentType.TXT:
                content = await self._load_text(source_path, encoding)
            elif doc_type == DocumentType.MD:
                content = await self._load_markdown(source_path, encoding)
            elif doc_type == DocumentType.HTML:
                content = await self._load_html(source_path, encoding)
            elif doc_type == DocumentType.JSON:
                content = await self._load_json(source_path, encoding)
            elif doc_type == DocumentType.CSV:
                content = await self._load_csv(source_path, encoding)
            elif doc_type == DocumentType.DOCX:
                content = await self._load_docx(source_path)
            else:
                raise DocumentLoadError(f"Unsupported format: {doc_type}")

            # Create and return document
            return self.create_document(
                title=source_path.stem,
                content=content,
                source=source_path,
                doc_type=doc_type,
                encoding=encoding
            )

        except Exception as e:
            if isinstance(e, DocumentLoadError):
                raise
            raise DocumentParseError(
                f"Failed to parse {doc_type.value} document",
                details={"source": str(source)},
                original_error=e
            )

    async def _load_text(self, path: Path, encoding: str) -> str:
        """Load plain text file."""
        async with aiofiles.open(path, mode='r', encoding=encoding) as f:
            content = await f.read()
        return content.strip()

    async def _load_markdown(self, path: Path, encoding: str) -> str:
        """
        Load Markdown file.

        Note: We keep the raw markdown content. If you want to convert
        to HTML or plain text, you can use libraries like markdown2 or mistune.
        """
        async with aiofiles.open(path, mode='r', encoding=encoding) as f:
            content = await f.read()
        return content.strip()

    async def _load_html(self, path: Path, encoding: str) -> str:
        """Load HTML file and extract text content."""
        async with aiofiles.open(path, mode='r', encoding=encoding) as f:
            html_content = await f.read()

        # Extract text from HTML using BeautifulSoup
        def extract_text():
            soup = BeautifulSoup(html_content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text
            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)

            return text

        # Run BeautifulSoup in thread pool (it's CPU-bound)
        return await asyncio.to_thread(extract_text)

    async def _load_json(self, path: Path, encoding: str) -> str:
        """
        Load JSON file and convert to readable text.

        Converts JSON structure to a formatted string representation.
        """
        async with aiofiles.open(path, mode='r', encoding=encoding) as f:
            json_content = await f.read()

        try:
            data = json.loads(json_content)
            # Pretty print JSON for better readability
            formatted = json.dumps(data, indent=2, ensure_ascii=False)
            return formatted
        except json.JSONDecodeError as e:
            raise DocumentParseError(
                f"Invalid JSON format",
                details={"path": str(path)},
                original_error=e
            )

    async def _load_csv(self, path: Path, encoding: str) -> str:
        """
        Load CSV file and convert to readable text.

        Converts CSV rows to formatted text with headers.
        """
        def read_csv():
            with open(path, mode='r', encoding=encoding, newline='') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

                if not rows:
                    return ""

                # Format as text
                lines = []
                headers = list(rows[0].keys())
                lines.append("Columns: " + ", ".join(headers))
                lines.append("")

                for i, row in enumerate(rows, 1):
                    lines.append(f"Row {i}:")
                    for key, value in row.items():
                        lines.append(f"  {key}: {value}")
                    lines.append("")

                return "\n".join(lines)

        try:
            return await asyncio.to_thread(read_csv)
        except Exception as e:
            raise DocumentParseError(
                f"Failed to parse CSV",
                details={"path": str(path)},
                original_error=e
            )

    async def _load_docx(self, path: Path) -> str:
        """
        Load Word document (.docx) and extract text.

        Uses python-docx library to extract paragraphs.
        """
        def extract_text():
            try:
                doc = DocxDocument(str(path))
                paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
                return "\n\n".join(paragraphs)
            except Exception as e:
                raise DocumentParseError(
                    f"Failed to parse DOCX document",
                    details={"path": str(path)},
                    original_error=e
                )

        return await asyncio.to_thread(extract_text)

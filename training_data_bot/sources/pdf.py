"""
PDF Loader - PDF Document Specialist

Handles loading and text extraction from PDF files using PyMuPDF (fitz).
"""

import asyncio
from pathlib import Path
from typing import Union

try:
    import pymupdf as fitz  # PyMuPDF (new import style)
except ImportError:
    import fitz  # PyMuPDF (legacy import)

from ..core.exceptions import DocumentLoadError, DocumentParseError
from ..core.models import Document, DocumentType
from .base import BaseLoader


class PDFLoader(BaseLoader):
    """
    Loader for PDF documents.

    Uses PyMuPDF (fitz) for fast and accurate PDF text extraction.
    """

    def __init__(self):
        super().__init__()
        self.supported_formats = [DocumentType.PDF]

    async def load_single(self, source: Union[str, Path], **kwargs) -> Document:
        """
        Load a single PDF document.

        Args:
            source: Path to the PDF file
            **kwargs: Additional options

        Returns:
            Document object with extracted text content
        """
        source_path = Path(source)
        self.validate_file_exists(source_path)

        self.logger.info(f"Loading PDF document: {source_path.name}")

        try:
            # Extract text from PDF
            content, page_count = await self._extract_pdf_text(source_path)

            # Create and return document
            return self.create_document(
                title=source_path.stem,
                content=content,
                source=source_path,
                doc_type=DocumentType.PDF,
                extraction_method="PyMuPDF",
                page_count=page_count
            )

        except Exception as e:
            if isinstance(e, DocumentLoadError):
                raise
            raise DocumentParseError(
                f"Failed to extract text from PDF",
                details={"source": str(source)},
                original_error=e
            )

    async def _extract_pdf_text(self, path: Path) -> tuple[str, int]:
        """
        Extract text from PDF using PyMuPDF.

        Args:
            path: Path to PDF file

        Returns:
            Tuple of (extracted_text, page_count)
        """
        def _extract_text():
            """Synchronous text extraction (runs in thread pool)."""
            try:
                # Open PDF
                doc = fitz.open(str(path))
                page_count = doc.page_count

                text_parts = []

                # Extract text from each page
                for page_num in range(page_count):
                    page = doc[page_num]
                    text = page.get_text()

                    # Only include pages with actual text
                    if text.strip():
                        text_parts.append(f"=== Page {page_num + 1} ===\n{text}")

                # Close document
                doc.close()

                # Combine all pages
                full_text = "\n\n".join(text_parts)

                return full_text, page_count

            except Exception as e:
                raise DocumentParseError(
                    f"PyMuPDF extraction failed",
                    details={"path": str(path)},
                    original_error=e
                )

        # Run in thread pool (PyMuPDF is CPU-bound)
        return await asyncio.to_thread(_extract_text)

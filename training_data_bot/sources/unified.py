"""
Unified Loader - The Traffic Controller

Auto-detects document type and routes to the appropriate specialized loader.
This is the main entry point for loading any type of document.
"""

import asyncio
from pathlib import Path
from typing import List, Union

from ..core.exceptions import DocumentLoadError, UnsupportedFormatError
from ..core.logging import LogContext
from ..core.models import Document, DocumentType
from .base import BaseLoader
from .document import DocumentLoader
from .pdf import PDFLoader
from .web import WebLoader


class UnifiedLoader(BaseLoader):
    """
    Unified loader that auto-detects document type and routes to specialized loaders.

    Think of this as a traffic controller that:
    1. Looks at what you're trying to load
    2. Figures out what type it is
    3. Sends it to the right specialist
    """

    def __init__(self):
        super().__init__()

        # Initialize specialized loaders
        self.document_loader = DocumentLoader()
        self.pdf_loader = PDFLoader()
        self.web_loader = WebLoader()

        # All supported formats
        self.supported_formats = list(DocumentType)

    async def close(self):
        """Close underlying specialized loaders."""
        if hasattr(self.web_loader, "close"):
            await self.web_loader.close()

    async def load_single(self, source: Union[str, Path], **kwargs) -> Document:
        """
        Auto-detect type and load a single document.

        Args:
            source: File path or URL to load
            **kwargs: Options passed to the specialized loader

        Returns:
            Document object with extracted content

        Example:
            loader = UnifiedLoader()

            # Load PDF
            doc1 = await loader.load_single("report.pdf")

            # Load website
            doc2 = await loader.load_single("https://example.com")

            # Load text file
            doc3 = await loader.load_single("notes.txt")
        """
        source_str = str(source)

        with LogContext(source=source_str):
            self.logger.info(f"Auto-detecting document type for: {source_str}")

            # Step 1: Is it a website?
            if source_str.startswith(('http://', 'https://')):
                self.logger.debug("Detected URL → routing to WebLoader")
                return await self.web_loader.load_single(source_str, **kwargs)

            # Step 2: Is it a file?
            source_path = Path(source_str)
            if not source_path.exists():
                raise DocumentLoadError(
                    f"File not found: {source_path}",
                    details={"source": source_str}
                )

            # Step 3: What type of file?
            try:
                doc_type = self.get_document_type(source_path)
            except DocumentLoadError as e:
                raise UnsupportedFormatError(
                    f"Cannot determine document type",
                    details={"source": source_str},
                    original_error=e
                )

            # Step 4: Route to specialized loader
            if doc_type == DocumentType.PDF:
                self.logger.debug("Detected PDF → routing to PDFLoader")
                return await self.pdf_loader.load_single(source_path, **kwargs)

            elif doc_type in [
                DocumentType.TXT, DocumentType.DOCX, DocumentType.MD,
                DocumentType.HTML, DocumentType.JSON, DocumentType.CSV
            ]:
                self.logger.debug(f"Detected {doc_type.value} → routing to DocumentLoader")
                return await self.document_loader.load_single(source_path, **kwargs)

            else:
                raise UnsupportedFormatError(
                    f"Unsupported document type: {doc_type.value}",
                    details={"source": source_str, "type": doc_type.value}
                )

    async def load_directory(
        self,
        directory: Union[str, Path],
        recursive: bool = True,
        max_workers: int = 4
    ) -> List[Document]:
        """
        Load all supported documents from a directory.

        Args:
            directory: Directory path to scan
            recursive: Search subdirectories recursively
            max_workers: Maximum concurrent loads

        Returns:
            List of loaded documents

        Example:
            loader = UnifiedLoader()
            docs = await loader.load_directory("./documents", recursive=True)
        """
        directory_path = Path(directory)

        if not directory_path.exists():
            raise DocumentLoadError(
                f"Directory not found: {directory}",
                details={"directory": str(directory)}
            )

        if not directory_path.is_dir():
            raise DocumentLoadError(
                f"Path is not a directory: {directory}",
                details={"directory": str(directory)}
            )

        self.logger.info(
            f"Scanning directory: {directory} (recursive={recursive})"
        )

        # Find all supported files
        patterns = ["*.pdf", "*.txt", "*.md", "*.html", "*.docx", "*.json", "*.csv"]
        sources = []

        for pattern in patterns:
            if recursive:
                sources.extend(directory_path.rglob(pattern))
            else:
                sources.extend(directory_path.glob(pattern))

        self.logger.info(f"Found {len(sources)} files to load")

        # Load all files
        return await self.load_multiple(sources, max_workers=max_workers)

    async def load_batch(
        self,
        sources: List[Union[str, Path]],
        max_workers: int = 4,
        stop_on_error: bool = False
    ) -> tuple[List[Document], List[tuple[str, Exception]]]:
        """
        Load multiple documents and collect both successes and failures.

        Args:
            sources: List of file paths or URLs
            max_workers: Maximum concurrent loads
            stop_on_error: Stop on first error (default: False)

        Returns:
            Tuple of (successful_documents, failed_sources_with_errors)

        Example:
            loader = UnifiedLoader()
            docs, failures = await loader.load_batch([
                "file1.pdf",
                "file2.txt",
                "https://example.com"
            ])

            print(f"Loaded: {len(docs)}, Failed: {len(failures)}")
        """
        self.logger.info(f"Batch loading {len(sources)} sources")

        semaphore = asyncio.Semaphore(max_workers)
        documents = []
        failures = []

        async def load_with_tracking(source):
            """Load and track success/failure."""
            async with semaphore:
                try:
                    doc = await self.load_single(source)
                    documents.append(doc)
                    return True
                except Exception as e:
                    failures.append((str(source), e))
                    self.logger.error(f"Failed to load {source}: {e}")
                    if stop_on_error:
                        raise
                    return False

        # Execute all loads
        await asyncio.gather(
            *[load_with_tracking(source) for source in sources],
            return_exceptions=not stop_on_error
        )

        self.logger.info(
            f"Batch complete: {len(documents)} succeeded, {len(failures)} failed"
        )

        return documents, failures

    def __repr__(self) -> str:
        """String representation."""
        return f"UnifiedLoader(loaders=[PDFLoader, WebLoader, DocumentLoader])"

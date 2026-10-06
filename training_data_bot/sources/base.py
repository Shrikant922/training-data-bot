"""
Base Loader - The Master Blueprint for Document Loaders

This module defines the abstract base class that all document loaders must follow.
Ensures consistent interface across all loader types.
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Union
from uuid import uuid4

from ..core.exceptions import DocumentLoadError
from ..core.logging import LogContext, get_logger
from ..core.models import Document, DocumentType


class BaseLoader(ABC):
    """
    Abstract base class for all document loaders.

    All loaders (PDF, Web, Document) inherit from this and must implement:
    - load_single(): Load one document

    Provides:
    - load_multiple(): Load multiple documents in parallel
    - get_document_type(): Auto-detect document type
    - create_document(): Factory method for Document objects
    """

    def __init__(self):
        """Initialize the loader with a logger and supported formats list."""
        self.logger = get_logger(f"loader.{self.__class__.__name__}")
        self.supported_formats: List[DocumentType] = []

    @abstractmethod
    async def load_single(self, source: Union[str, Path], **kwargs) -> Document:
        """
        Load a single document from the given source.

        Args:
            source: File path or URL to load
            **kwargs: Loader-specific options

        Returns:
            Document object with extracted content

        Raises:
            DocumentLoadError: If loading fails
        """
        pass

    async def load_multiple(
        self,
        sources: List[Union[str, Path]],
        max_workers: int = 4
    ) -> List[Document]:
        """
        Load multiple documents in parallel with controlled concurrency.

        Args:
            sources: List of file paths or URLs to load
            max_workers: Maximum number of concurrent loads

        Returns:
            List of successfully loaded Document objects

        Example:
            loader = PDFLoader()
            docs = await loader.load_multiple(["file1.pdf", "file2.pdf"], max_workers=2)
        """
        self.logger.info(f"Loading {len(sources)} documents with {max_workers} workers")

        # Semaphore to limit concurrent operations
        semaphore = asyncio.Semaphore(max_workers)

        async def load_with_semaphore(source):
            """Wrapper to load with semaphore control."""
            async with semaphore:
                with LogContext(source=str(source)):
                    try:
                        return await self.load_single(source)
                    except Exception as e:
                        self.logger.error(f"Failed to load {source}: {e}")
                        return None

        # Execute all loads concurrently
        tasks = [load_with_semaphore(source) for source in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out failures and exceptions
        documents = []
        for result in results:
            if isinstance(result, Document):
                documents.append(result)
            elif isinstance(result, Exception):
                self.logger.error(f"Load error: {result}")
            # None results (caught exceptions) are already logged

        self.logger.info(
            f"Successfully loaded {len(documents)}/{len(sources)} documents"
        )
        return documents

    def get_document_type(self, source: Union[str, Path]) -> DocumentType:
        """
        Auto-detect document type from source.

        Args:
            source: File path or URL

        Returns:
            DocumentType enum value

        Raises:
            DocumentLoadError: If type cannot be determined
        """
        source_str = str(source)

        # Check if URL
        if source_str.startswith(('http://', 'https://')):
            return DocumentType.URL

        # Check file extension
        source_path = Path(source_str)
        suffix = source_path.suffix.lower().lstrip('.')

        if not suffix:
            raise DocumentLoadError(f"Cannot determine document type: {source}")

        try:
            return DocumentType(suffix)
        except ValueError:
            raise DocumentLoadError(
                f"Unsupported document type: {suffix}",
                details={"source": str(source), "extension": suffix}
            )

    def create_document(
        self,
        title: str,
        content: str,
        source: Union[str, Path],
        doc_type: DocumentType,
        **kwargs
    ) -> Document:
        """
        Factory method to create a standardized Document object.

        Args:
            title: Document title
            content: Extracted text content
            source: Original source location
            doc_type: Type of document
            **kwargs: Additional metadata to include

        Returns:
            Document object with all fields populated
        """
        # Calculate statistics
        word_count = len(content.split())
        char_count = len(content)

        # Build metadata
        metadata = {
            "loader": self.__class__.__name__,
            "loaded_at": datetime.utcnow().isoformat(),
            **kwargs
        }

        # Create and return document
        document = Document(
            id=uuid4(),
            title=title,
            content=content,
            source=str(source),
            doc_type=doc_type,
            word_count=word_count,
            char_count=char_count,
            created_at=datetime.utcnow(),
            metadata=metadata
        )

        self.logger.debug(
            f"Created document: {title} ({word_count} words, {char_count} chars)"
        )

        return document

    def validate_file_exists(self, path: Path) -> None:
        """
        Validate that a file exists and is readable.

        Args:
            path: File path to validate

        Raises:
            DocumentLoadError: If file doesn't exist or isn't readable
        """
        if not path.exists():
            raise DocumentLoadError(
                f"File not found: {path}",
                details={"path": str(path)}
            )

        if not path.is_file():
            raise DocumentLoadError(
                f"Path is not a file: {path}",
                details={"path": str(path)}
            )

    def __repr__(self) -> str:
        """String representation of the loader."""
        formats = ", ".join(f.value for f in self.supported_formats)
        return f"{self.__class__.__name__}(formats=[{formats}])"

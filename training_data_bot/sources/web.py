"""
Web Loader - Website Content Specialist

Handles loading and text extraction from web URLs using httpx and BeautifulSoup.
"""

import asyncio
from typing import Union
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from ..core.config import settings
from ..core.exceptions import HTTPError, URLError, WebLoadError
from ..core.models import Document, DocumentType
from .base import BaseLoader


class WebLoader(BaseLoader):
    """
    Loader for web content (URLs).

    Uses httpx for async HTTP requests and BeautifulSoup for HTML parsing.
    """

    def __init__(self, request_delay: float = 0.0):
        super().__init__()
        self.supported_formats = [DocumentType.URL]
        self.request_delay = request_delay
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or initialize the reusable httpx AsyncClient for connection pooling."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=settings.web_timeout,
                max_redirects=settings.web_max_redirects,
                verify=settings.web_verify_ssl,
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
            )
        return self._client

    async def close(self):
        """Close persistent HTTP client session."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def load_single(self, source: Union[str, str], **kwargs) -> Document:
        """
        Load content from a web URL.

        Args:
            source: URL to load
            **kwargs: Additional options (timeout, headers, etc.)

        Returns:
            Document object with extracted web content
        """
        url = str(source)

        # Validate URL format
        if not url.startswith(('http://', 'https://')):
            raise URLError(
                f"Invalid URL scheme (must be http:// or https://)",
                details={"url": url}
            )

        self.logger.info(f"Loading web content from: {url}")

        try:
            # Fetch content
            content, content_type = await self._fetch_url_content(url, **kwargs)

            # Extract title
            title = self._extract_title(url, content, content_type)

            # Create and return document
            return self.create_document(
                title=title,
                content=content,
                source=url,
                doc_type=DocumentType.URL,
                extraction_method="httpx+BeautifulSoup",
                content_type=content_type
            )

        except HTTPError:
            raise
        except Exception as e:
            if isinstance(e, WebLoadError):
                raise
            raise WebLoadError(
                f"Failed to load web content from {url}",
                details={"url": url},
                original_error=e
            )

    async def _fetch_url_content(
        self,
        url: str,
        timeout: float = None,
        headers: dict = None,
        **kwargs
    ) -> tuple[str, str]:
        """
        Fetch content from URL using pooled httpx client.

        Args:
            url: URL to fetch
            timeout: Request timeout in seconds
            headers: Custom HTTP headers
            **kwargs: Additional httpx options

        Returns:
            Tuple of (extracted_text, content_type)
        """
        # Optional polite delay (0.0 by default for max performance)
        delay = kwargs.get("delay", self.request_delay)
        if delay > 0:
            await asyncio.sleep(delay)

        # Use browser-like headers to avoid being blocked
        # Wikipedia requires proper identification
        default_headers = {
            "User-Agent": "TrainingDataBot/1.0 (Educational/Research; Python/httpx) - Contact: educational.research@example.com",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

        if headers:
            default_headers.update(headers)

        try:
            client = await self._get_client()
            req_timeout = timeout or settings.web_timeout
            response = await client.get(url, headers=default_headers, timeout=req_timeout)

            # Check for HTTP errors
            if response.status_code >= 400:
                raise HTTPError(
                    f"HTTP {response.status_code} error",
                    status_code=response.status_code,
                    url=url
                )

            response.raise_for_status()

            # Get content type
            content_type = response.headers.get('content-type', '').lower()

            # Handle different content types
            if 'text/html' in content_type:
                # Extract text from HTML
                text = await asyncio.to_thread(
                    self._extract_html_text,
                    response.text
                )
            elif 'text/' in content_type:
                # Plain text or other text formats
                text = response.text
            else:
                # Unsupported content type
                raise WebLoadError(
                    f"Unsupported content type: {content_type}",
                    details={"url": url, "content_type": content_type}
                )

            return text, content_type

        except httpx.TimeoutException as e:
            raise HTTPError(
                f"Request timeout after {timeout}s",
                url=url,
                original_error=e
            )
        except httpx.HTTPError as e:
            raise HTTPError(
                f"HTTP error occurred",
                url=url,
                original_error=e
            )

    def _extract_html_text(self, html: str) -> str:
        """
        Extract clean text from HTML content.

        Args:
            html: Raw HTML string

        Returns:
            Cleaned text content
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style", "meta", "link"]):
            script.decompose()

        # Get text
        text = soup.get_text()

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = ' '.join(chunk for chunk in chunks if chunk)

        return clean_text

    def _extract_title(self, url: str, content: str, content_type: str) -> str:
        """
        Extract or generate a title for the web document.

        Args:
            url: Source URL
            content: Page content (HTML or text)
            content_type: Content-Type header value

        Returns:
            Document title
        """
        # Try to extract title from HTML
        if 'text/html' in content_type:
            try:
                soup = BeautifulSoup(content, 'html.parser')
                title_tag = soup.find('title')
                if title_tag and title_tag.text.strip():
                    return title_tag.text.strip()
            except Exception:
                pass  # Fall through to URL-based title

        # Fall back to URL-based title
        parsed = urlparse(url)
        # Use domain + path as title
        title = parsed.netloc + parsed.path

        # Clean up title
        if title.endswith('/'):
            title = title[:-1]
        if not title:
            title = url

        return title

    async def load_multiple(
        self,
        sources: list[Union[str, str]],
        max_workers: int = 4
    ) -> list[Document]:
        """
        Override load_multiple to respect rate limiting for web requests.

        Args:
            sources: List of URLs to load
            max_workers: Maximum concurrent requests

        Returns:
            List of successfully loaded documents
        """
        # Use lower concurrency for web requests to be polite
        max_workers = min(max_workers, 3)
        return await super().load_multiple(sources, max_workers)

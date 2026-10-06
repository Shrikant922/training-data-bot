"""
Decodo Client - Advanced Web Scraping (Optional)

Optional integration with Decodo API for advanced web scraping capabilities.
Falls back to standard WebLoader if not configured.
"""

from typing import Optional

import httpx

from ..core.config import settings
from ..core.exceptions import DecodoAPIError, DecodoAuthError, DecodoError
from ..core.logging import get_logger


class DecodoClient:
    """
    Optional Decodo API client for advanced web scraping.

    Note: This is a placeholder implementation. In production, integrate
    with actual Decodo API according to their documentation.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize the Decodo client.

        Args:
            api_key: Decodo API key (uses settings if not provided)
            base_url: Decodo API base URL (uses settings if not provided)
        """
        self.logger = get_logger("decodo_client")
        self.api_key = api_key or settings.decodo_api_key
        self.base_url = base_url or settings.decodo_base_url

        if not self.api_key:
            self.logger.warning("No Decodo API key configured - Decodo features disabled")
            self._enabled = False
        else:
            self._enabled = True
            self.logger.info("Decodo client initialized")

    async def scrape_url(self, url: str, **kwargs) -> str:
        """
        Scrape content from a URL using Decodo API.

        Args:
            url: URL to scrape
            **kwargs: Additional Decodo API parameters

        Returns:
            Scraped content as text

        Raises:
            DecodoError: If scraping fails
        """
        if not self._enabled:
            raise DecodoError("Decodo API not configured")

        self.logger.info(f"Scraping URL with Decodo: {url}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/scrape",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "url": url,
                        **kwargs
                    },
                    timeout=30.0
                )

                if response.status_code == 401:
                    raise DecodoAuthError(
                        "Decodo authentication failed",
                        details={"url": url}
                    )

                if response.status_code != 200:
                    raise DecodoAPIError(
                        f"Decodo API error: {response.status_code}",
                        details={"url": url, "status": response.status_code}
                    )

                data = response.json()
                content = data.get("content", "")

                self.logger.info(f"Successfully scraped {len(content)} characters")
                return content

        except httpx.HTTPError as e:
            raise DecodoAPIError(
                "Decodo request failed",
                details={"url": url},
                original_error=e
            )

    def is_enabled(self) -> bool:
        """Check if Decodo features are enabled."""
        return self._enabled

    async def close(self):
        """Close Decodo client and cleanup resources."""
        if self._enabled:
            self.logger.info("Decodo client closed")

    def __repr__(self) -> str:
        """String representation."""
        status = "enabled" if self._enabled else "disabled"
        return f"DecodoClient(status={status})"

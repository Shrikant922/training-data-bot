"""
AI Client - LLM Integration

Handles communication with AI providers (OpenAI, Anthropic) for text generation tasks.
Supports multiple providers with automatic fallback and rate limiting.
"""

import asyncio
from typing import Any, Dict, List, Optional

from ..core.config import settings
from ..core.exceptions import (
    AIClientError,
    APIKeyError,
    APIRequestError,
    RateLimitError,
    TokenLimitError,
)
from ..core.logging import LogContext, get_logger
from ..storage.cache import CacheManager


class AIClient:
    """
    Unified AI client supporting multiple LLM providers.

    Supports:
    - OpenAI (GPT-4, GPT-3.5)
    - Anthropic (Claude)
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Initialize the AI client.

        Args:
            provider: AI provider ("openai" or "anthropic")
            api_key: API key (overrides settings)
            model: Model name (overrides settings)
        """
        self.logger = get_logger("ai_client")
        self.provider = provider or settings.default_ai_provider

        # Set up provider-specific configuration
        if self.provider == "openai":
            self.api_key = api_key or settings.openai_api_key
            self.model = model or settings.openai_model
            self.temperature = settings.openai_temperature
            self.max_tokens = settings.openai_max_tokens
        elif self.provider == "anthropic":
            self.api_key = api_key or settings.anthropic_api_key
            self.model = model or settings.anthropic_model
            self.temperature = settings.anthropic_temperature
            self.max_tokens = settings.anthropic_max_tokens
        else:
            raise AIClientError(
                f"Unsupported AI provider: {self.provider}",
                details={"provider": self.provider}
            )

        # NOTE: API key validation is lazy — we don't raise here so the bot
        # can be constructed even without a key (useful for testing loaders,
        # preprocessors, exporters etc. without needing AI access).
        # The key is validated in generate() when actually needed.
        self._client = None

        # Intelligent SQLite-backed response cache
        self.cache = CacheManager(enabled=settings.enable_cache)

        self.logger.info(f"Initialized AI client: {self.provider} / {self.model}")

    def _init_client(self):
        """Initialize the provider-specific client (lazy — called on first generate())."""
        if self._client is not None:
            return  # Already initialized

        # Validate API key now that we actually need it
        if not self.api_key:
            raise APIKeyError(
                f"API key not found for provider: {self.provider}. "
                f"Set TRAINING_DATA_BOT_{self.provider.upper()}_API_KEY in your .env file.",
                details={"provider": self.provider}
            )

        try:
            if self.provider == "openai":
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.api_key)
            elif self.provider == "anthropic":
                from anthropic import AsyncAnthropic
                self._client = AsyncAnthropic(api_key=self.api_key)
        except ImportError as e:
            raise AIClientError(
                f"Provider SDK not installed: {self.provider}. "
                f"Run: pip install {self.provider}",
                details={"provider": self.provider},
                original_error=e
            )

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate text using the AI model.

        Args:
            prompt: User prompt/input
            system_prompt: System instruction (optional)
            temperature: Sampling temperature (overrides default)
            max_tokens: Maximum tokens to generate (overrides default)
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated text

        Example:
            client = AIClient()
            response = await client.generate(
                prompt="What is machine learning?",
                system_prompt="You are a helpful AI assistant."
            )
        """
        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens if max_tokens is not None else self.max_tokens

        use_cache = kwargs.pop("use_cache", True)
        cache_key = None
        if use_cache and self.cache.enabled:
            cache_key = CacheManager.make_key(
                provider=self.provider,
                model=self.model,
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
            cached_response = self.cache.get(cache_key)
            if cached_response is not None:
                self.logger.info(f"Retrieved response from cache ({len(cached_response)} chars)")
                return cached_response

        # Lazy-initialize the client on first use
        self._init_client()

        with LogContext(provider=self.provider, model=self.model):
            self.logger.debug(f"Generating with prompt length: {len(prompt)}")

            try:
                if self.provider == "openai":
                    response = await self._generate_openai(
                        prompt, system_prompt, temperature, max_tokens, **kwargs
                    )
                elif self.provider == "anthropic":
                    response = await self._generate_anthropic(
                        prompt, system_prompt, temperature, max_tokens, **kwargs
                    )
                else:
                    raise AIClientError(f"Unsupported provider: {self.provider}")

                self.logger.debug(f"Generated response length: {len(response)}")

                # Save response to cache for zero-cost instant retrieval on future runs
                if cache_key and self.cache.enabled:
                    self.cache.set(
                        cache_key,
                        response,
                        provider=self.provider,
                        model=self.model
                    )

                return response

            except Exception as e:
                if isinstance(e, AIClientError):
                    raise
                raise APIRequestError(
                    f"AI generation failed",
                    provider=self.provider,
                    model=self.model,
                    original_error=e
                )

    async def _generate_openai(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> str:
        """Generate using OpenAI API."""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            return response.choices[0].message.content

        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "quota" in error_str:
                raise RateLimitError(
                    "OpenAI rate limit exceeded",
                    details={"model": self.model},
                    original_error=e
                )
            elif "token" in error_str and "limit" in error_str:
                raise TokenLimitError(
                    "Token limit exceeded",
                    details={"model": self.model, "max_tokens": max_tokens},
                    original_error=e
                )
            raise

    async def _generate_anthropic(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> str:
        """Generate using Anthropic API."""
        try:
            params = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
                **kwargs
            }

            if system_prompt:
                params["system"] = system_prompt

            response = await self._client.messages.create(**params)

            return response.content[0].text

        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "quota" in error_str:
                raise RateLimitError(
                    "Anthropic rate limit exceeded",
                    details={"model": self.model},
                    original_error=e
                )
            elif "token" in error_str and "limit" in error_str:
                raise TokenLimitError(
                    "Token limit exceeded",
                    details={"model": self.model, "max_tokens": max_tokens},
                    original_error=e
                )
            raise

    async def generate_batch(
        self,
        prompts: List[str],
        system_prompt: Optional[str] = None,
        max_concurrent: int = None,
        **kwargs
    ) -> List[str]:
        """
        Generate responses for multiple prompts in parallel.

        Args:
            prompts: List of prompts
            system_prompt: System instruction
            max_concurrent: Maximum concurrent requests
            **kwargs: Additional generation parameters

        Returns:
            List of generated responses

        Example:
            responses = await client.generate_batch([
                "What is AI?",
                "What is ML?",
                "What is DL?"
            ])
        """
        max_concurrent = max_concurrent or settings.max_concurrent_requests

        self.logger.info(f"Batch generating {len(prompts)} prompts")

        semaphore = asyncio.Semaphore(max_concurrent)

        async def generate_with_semaphore(prompt):
            async with semaphore:
                return await self.generate(prompt, system_prompt, **kwargs)

        results = await asyncio.gather(
            *[generate_with_semaphore(p) for p in prompts],
            return_exceptions=True
        )

        # Log any errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Batch item {i} failed: {result}")

        return results

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Rough approximation: 1 token ≈ 4 characters for English text.

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        return len(text) // 4

    async def close(self):
        """Close the AI client and cleanup resources."""
        if self._client:
            if hasattr(self._client, 'close'):
                await self._client.close()
            self._client = None
        self.logger.info("AI client closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def __repr__(self) -> str:
        """String representation."""
        return f"AIClient(provider={self.provider}, model={self.model})"

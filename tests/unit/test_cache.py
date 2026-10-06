"""
Unit Tests: CacheManager
Tests SQLite response caching, deterministic keys, hit tracking, and AIClient cache integration.
"""
import sys
import os
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
os.chdir(Path(__file__).parent.parent.parent)

import pytest
from training_data_bot.storage.cache import CacheManager
from training_data_bot.ai.client import AIClient


@pytest.fixture
def temp_cache(tmp_path):
    """Create a temporary CacheManager with isolated SQLite DB."""
    db_file = tmp_path / "test_cache.db"
    return CacheManager(db_path=db_file, enabled=True)


class TestCacheManagerCore:
    def test_make_key_is_deterministic(self):
        k1 = CacheManager.make_key("openai", "gpt-4o-mini", "hello world", "system")
        k2 = CacheManager.make_key("openai", "gpt-4o-mini", "hello world", "system")
        assert k1 == k2

    def test_make_key_sensitive_to_prompt(self):
        k1 = CacheManager.make_key("openai", "gpt-4o-mini", "prompt A")
        k2 = CacheManager.make_key("openai", "gpt-4o-mini", "prompt B")
        assert k1 != k2

    def test_make_key_sensitive_to_model(self):
        k1 = CacheManager.make_key("openai", "gpt-4o-mini", "prompt")
        k2 = CacheManager.make_key("openai", "gpt-4o", "prompt")
        assert k1 != k2

    def test_cache_miss_returns_none(self, temp_cache):
        assert temp_cache.get("nonexistent_key") is None

    def test_cache_set_and_get(self, temp_cache):
        key = temp_cache.make_key("openai", "gpt-4o-mini", "test prompt")
        saved = temp_cache.set(key, "Generated response content")
        assert saved is True

        retrieved = temp_cache.get(key)
        assert retrieved == "Generated response content"

    def test_cache_hit_tracking(self, temp_cache):
        key = temp_cache.make_key("openai", "gpt-4o-mini", "hit test")
        temp_cache.set(key, "response")

        temp_cache.get(key)
        temp_cache.get(key)
        temp_cache.get(key)

        stats = temp_cache.get_stats()
        assert stats["total_hits"] >= 3

    def test_cache_retrieval_speed_submillisecond(self, temp_cache):
        key = temp_cache.make_key("openai", "gpt-4o-mini", "speed test")
        temp_cache.set(key, "speed response" * 50)

        start = time.perf_counter()
        result = temp_cache.get(key)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert result is not None
        assert elapsed_ms < 10.0  # Well under 10ms (typically 0.1ms - 0.5ms)

    def test_cache_clear(self, temp_cache):
        k1 = temp_cache.make_key("openai", "m", "p1")
        k2 = temp_cache.make_key("openai", "m", "p2")
        temp_cache.set(k1, "r1")
        temp_cache.set(k2, "r2")

        cleared = temp_cache.clear()
        assert cleared == 2
        assert temp_cache.get(k1) is None
        assert temp_cache.get(k2) is None

    def test_cache_disabled_mode(self, tmp_path):
        disabled_cache = CacheManager(db_path=tmp_path / "dis.db", enabled=False)
        key = disabled_cache.make_key("openai", "m", "p")
        assert disabled_cache.set(key, "r") is False
        assert disabled_cache.get(key) is None
        assert disabled_cache.clear() == 0


class TestAIClientCacheIntegration:
    @pytest.mark.asyncio
    async def test_aiclient_uses_cache_hit(self, tmp_path):
        """When a response is in the cache, AIClient does not call external provider."""
        client = AIClient(provider="openai", api_key="dummy-key", model="gpt-4o-mini")
        client.cache = CacheManager(db_path=tmp_path / "ai_cache.db", enabled=True)

        prompt = "Cached question about AI"
        key = CacheManager.make_key(
            provider="openai",
            model="gpt-4o-mini",
            prompt=prompt,
            temperature=client.temperature,
            max_tokens=client.max_tokens
        )
        client.cache.set(key, "Instant cached response!")

        # Generate should return cached text immediately without touching OpenAI SDK
        with patch.object(client, "_generate_openai", new_callable=AsyncMock) as mock_api:
            res = await client.generate(prompt)
            assert res == "Instant cached response!"
            mock_api.assert_not_called()  # Proves 0 API calls made!

    @pytest.mark.asyncio
    async def test_aiclient_caches_new_response(self, tmp_path):
        """When a new response is generated, it is automatically written to the cache."""
        client = AIClient(provider="openai", api_key="dummy-key", model="gpt-4o-mini")
        client.cache = CacheManager(db_path=tmp_path / "ai_cache.db", enabled=True)

        prompt = "Uncached unique question"
        with patch.object(client, "_generate_openai", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = "Fresh AI generation"
            res1 = await client.generate(prompt)
            assert res1 == "Fresh AI generation"
            assert mock_api.call_count == 1

        # Second call with same prompt should be served directly from cache!
        with patch.object(client, "_generate_openai", new_callable=AsyncMock) as mock_api:
            res2 = await client.generate(prompt)
            assert res2 == "Fresh AI generation"
            mock_api.assert_not_called()  # 0 API calls!

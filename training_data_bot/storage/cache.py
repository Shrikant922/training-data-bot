"""
Intelligent Response Cache - High Performance SQLite Cache
Stores AI generation responses by hash of (provider, model, prompt, system_prompt, params).
Returns identical chunk generations in < 1 ms with 0 API cost.
"""

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ..core.config import settings
from ..core.logging import get_logger


class CacheManager:
    """
    Thread-safe SQLite-backed response cache for AIClient.

    Keyed on SHA-256 hash of:
      provider + model + system_prompt + prompt + relevant parameters

    Provides:
      - get(): O(1) indexed lookup in < 1ms
      - set(): persistent storage of results
      - stats(): hit count and cached item tracking
      - clear(): purge cache
    """

    def __init__(self, db_path: Optional[Path] = None, enabled: bool = True):
        self.logger = get_logger("cache_manager")
        self.enabled = enabled

        if db_path is None:
            cache_dir = Path(".cache")
            cache_dir.mkdir(exist_ok=True)
            self.db_path = cache_dir / "ai_cache.db"
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        if self.enabled:
            self._init_db()

    def _init_db(self) -> None:
        """Initialize the SQLite database schema with indexes."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS response_cache (
                        cache_key TEXT PRIMARY KEY,
                        provider TEXT NOT NULL,
                        model TEXT NOT NULL,
                        prompt_hash TEXT NOT NULL,
                        response TEXT NOT NULL,
                        task_type TEXT,
                        created_at TEXT NOT NULL,
                        last_accessed_at TEXT NOT NULL,
                        hit_count INTEGER DEFAULT 0
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_prompt_hash 
                    ON response_cache(prompt_hash)
                """)
                conn.commit()
            self.logger.debug(f"Cache initialized at {self.db_path}")
        except Exception as e:
            self.logger.warning(f"Failed to initialize cache DB: {e}. Cache disabled.")
            self.enabled = False

    @staticmethod
    def make_key(
        provider: str,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        **params: Any
    ) -> str:
        """
        Generate a deterministic SHA-256 cache key from request parameters.
        """
        key_payload = {
            "provider": provider.strip().lower(),
            "model": model.strip().lower(),
            "system_prompt": (system_prompt or "").strip(),
            "prompt": prompt.strip(),
            # Filter to deterministic generation parameters
            "temperature": params.get("temperature", 0.7),
            "max_tokens": params.get("max_tokens", 1000),
        }
        serialized = json.dumps(key_payload, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def get(self, cache_key: str) -> Optional[str]:
        """
        Retrieve cached response by cache_key.

        Returns:
            Cached response string, or None on cache miss.
        """
        if not self.enabled:
            return None

        try:
            with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT response, hit_count FROM response_cache
                    WHERE cache_key = ?
                    """,
                    (cache_key,)
                )
                row = cursor.fetchone()
                if row:
                    response, hit_count = row
                    # Update hit count and timestamp asynchronously
                    cursor.execute(
                        """
                        UPDATE response_cache
                        SET hit_count = hit_count + 1, last_accessed_at = ?
                        WHERE cache_key = ?
                        """,
                        (datetime.utcnow().isoformat(), cache_key)
                    )
                    conn.commit()
                    self.logger.debug(f"Cache HIT for key {cache_key[:8]}... (hits: {hit_count + 1})")
                    return response

            self.logger.debug(f"Cache MISS for key {cache_key[:8]}...")
            return None

        except Exception as e:
            self.logger.warning(f"Cache get error: {e}")
            return None

    def set(
        self,
        cache_key: str,
        response: str,
        provider: str = "",
        model: str = "",
        task_type: Optional[str] = None
    ) -> bool:
        """
        Store a response in the cache.

        Returns:
            True if stored successfully, False otherwise.
        """
        if not self.enabled:
            return False

        try:
            now = datetime.utcnow().isoformat()
            prompt_hash = cache_key[:16]
            with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO response_cache 
                    (cache_key, provider, model, prompt_hash, response, task_type, created_at, last_accessed_at, hit_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    (cache_key, provider, model, prompt_hash, response, task_type, now, now)
                )
                conn.commit()
            self.logger.debug(f"Cached response for key {cache_key[:8]}...")
            return True

        except Exception as e:
            self.logger.warning(f"Cache set error: {e}")
            return False

    def clear(self) -> int:
        """
        Clear all entries from the cache.

        Returns:
            Number of deleted records.
        """
        if not self.enabled:
            return 0

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM response_cache")
                count = cursor.rowcount
                conn.commit()
            self.logger.info(f"Cleared {count} items from cache")
            return count
        except Exception as e:
            self.logger.warning(f"Cache clear error: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        """
        if not self.enabled or not self.db_path.exists():
            return {"enabled": False, "total_entries": 0, "total_hits": 0, "size_bytes": 0}

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*), COALESCE(SUM(hit_count), 0) FROM response_cache")
                count, hits = cursor.fetchone()

            size_bytes = self.db_path.stat().st_size
            return {
                "enabled": True,
                "total_entries": count,
                "total_hits": hits,
                "size_bytes": size_bytes,
                "db_path": str(self.db_path)
            }
        except Exception as e:
            self.logger.warning(f"Cache stats error: {e}")
            return {"enabled": self.enabled, "error": str(e)}

    def __repr__(self) -> str:
        status = "enabled" if self.enabled else "disabled"
        return f"CacheManager(status={status}, db={self.db_path.name})"

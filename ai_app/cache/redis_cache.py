"""Redis cache and session management."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None


async def initialize_redis() -> redis.Redis:
    """Initialize and return the Redis client singleton."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    url = "redis://localhost:6379"
    password: Optional[str] = None
    db = 0

    try:
        import os

        url = os.environ.get("REDIS_URL", url)
        password = os.environ.get("REDIS_PASSWORD") or None
        db = int(os.environ.get("REDIS_DB", "0"))
    except Exception:
        pass

    logger.info("🔴 Connecting to Redis...")

    _redis_client = redis.Redis(
        host=url.split("://")[-1].split(":")[0] if "://" in url else url,
        port=int(url.split(":")[-1]) if ":" in url else 6379,
        password=password,
        db=db,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )

    try:
        await _redis_client.ping()
        logger.info("✅ Redis connection established")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        raise

    return _redis_client


def get_redis_client() -> redis.Redis:
    """Get the Redis client (must call initialize_redis first)."""
    if _redis_client is None:
        raise RuntimeError("Redis not initialized. Call initialize_redis() first.")
    return _redis_client


async def close_redis() -> None:
    """Close the Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("🔴 Redis connection closed")


# ---------------------------------------------------------------------------
# RedisCache helper
# ---------------------------------------------------------------------------


class RedisCache:
    """Simple key-value cache backed by Redis."""

    def __init__(self, client: Optional[redis.Redis] = None):
        self._client = client

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = get_redis_client()
        return self._client

    async def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """Set a cache value with TTL."""
        serialized = json.dumps(value, ensure_ascii=False, default=str)
        await self.client.setex(key, ttl_seconds, serialized)

    async def get(self, key: str) -> Optional[Any]:
        """Get a cache value."""
        value = await self.client.get(key)
        if value is None:
            return None
        return json.loads(value)

    async def delete(self, key: str) -> None:
        """Delete a cache key."""
        await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        return await self.client.exists(key) == 1

    async def expire(self, key: str, ttl_seconds: int) -> None:
        """Set TTL for an existing key."""
        await self.client.expire(key, ttl_seconds)

    async def ttl(self, key: str) -> int:
        """Get remaining TTL for a key."""
        return await self.client.ttl(key)


# ---------------------------------------------------------------------------
# SessionManager helper
# ---------------------------------------------------------------------------


class SessionManager:
    """Session data management using Redis."""

    def __init__(self):
        self._cache = RedisCache()

    async def set_session(
        self, session_id: str, data: Any, ttl_seconds: int = 86400
    ) -> None:
        """Store session data."""
        key = f"session:{session_id}"
        await self._cache.set(key, data, ttl_seconds)

    async def get_session(self, session_id: str) -> Optional[Any]:
        """Retrieve session data."""
        key = f"session:{session_id}"
        return await self._cache.get(key)

    async def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        key = f"session:{session_id}"
        await self._cache.delete(key)

    async def session_exists(self, session_id: str) -> bool:
        """Check if a session exists."""
        key = f"session:{session_id}"
        return await self._cache.exists(key)

    async def refresh_session(self, session_id: str, ttl_seconds: int = 86400) -> None:
        """Refresh session TTL."""
        key = f"session:{session_id}"
        await self._cache.expire(key, ttl_seconds)

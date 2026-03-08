"""
HostingSignal Panel — Redis Client
Connection and caching utilities for Redis.
"""
import json
from typing import Optional, Any

from config import settings

# Use optional import — Redis may not be installed in dev mode
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class RedisClient:
    """Async Redis client for caching and pub/sub."""

    def __init__(self):
        self._pool = None

    async def connect(self):
        """Create Redis connection pool."""
        if not REDIS_AVAILABLE:
            print("⚠️  Redis module not available — caching disabled")
            return
        try:
            redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
            self._pool = aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
            )
            await self._pool.ping()
            print("✅ Redis connected")
        except Exception as e:
            print(f"⚠️  Redis connection failed: {e}")
            self._pool = None

    async def disconnect(self):
        """Close Redis connection."""
        if self._pool:
            await self._pool.close()

    async def get(self, key: str) -> Optional[str]:
        """Get a value from cache."""
        if not self._pool:
            return None
        try:
            return await self._pool.get(key)
        except Exception:
            return None

    async def set(self, key: str, value: Any, expire: int = 300) -> bool:
        """Set a value in cache with TTL (default 5 minutes)."""
        if not self._pool:
            return False
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            await self._pool.setex(key, expire, value)
            return True
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        if not self._pool:
            return False
        try:
            await self._pool.delete(key)
            return True
        except Exception:
            return False

    async def get_json(self, key: str) -> Optional[Any]:
        """Get a JSON value from cache."""
        data = await self.get(key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return data
        return None

    async def publish(self, channel: str, message: dict):
        """Publish a message to a Redis channel."""
        if not self._pool:
            return
        try:
            await self._pool.publish(channel, json.dumps(message))
        except Exception:
            pass


# Singleton instance
redis_client = RedisClient()

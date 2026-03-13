import redis.asyncio as redis
from app.core.config import get_settings

settings = get_settings()

redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
    return redis_client


async def publish_event(stream: str, data: dict) -> str:
    """Publish an event to a Redis Stream."""
    client = await get_redis()
    message_id = await client.xadd(stream, data)
    return message_id


# ── Caching helpers ──

async def cache_set(key: str, value: str, ttl_seconds: int = 3600) -> None:
    """Set a cached value with TTL."""
    client = await get_redis()
    await client.setex(key, ttl_seconds, value)


async def cache_get(key: str) -> str | None:
    """Get a cached value."""
    client = await get_redis()
    return await client.get(key)


async def cache_delete(key: str) -> None:
    """Delete a cached value."""
    client = await get_redis()
    await client.delete(key)


# ── Session helpers ──

async def store_session(user_id: str, data: str, ttl_seconds: int = 86400) -> None:
    """Store user session metadata in Redis."""
    client = await get_redis()
    await client.setex(f"session:{user_id}", ttl_seconds, data)


async def get_session(user_id: str) -> str | None:
    """Retrieve user session metadata."""
    client = await get_redis()
    return await client.get(f"session:{user_id}")


async def invalidate_session(user_id: str) -> None:
    """Invalidate a user session."""
    client = await get_redis()
    await client.delete(f"session:{user_id}")


# ── Rate Limiting ──

async def check_rate_limit(
    key: str,
    max_requests: int = 60,
    window_seconds: int = 60,
) -> bool:
    """Simple sliding window rate limiter. Returns True if allowed."""
    client = await get_redis()
    current = await client.incr(f"rate:{key}")
    if current == 1:
        await client.expire(f"rate:{key}", window_seconds)
    return current <= max_requests


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None

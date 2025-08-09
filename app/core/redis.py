from redis.asyncio import Redis
from app.core.config import settings

redis: Redis | None = None

async def get_redis() -> Redis:
    global redis
    if redis is None:
        redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis

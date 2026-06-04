import redis.asyncio as aioredis
from app.core.config import settings

redis_pool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True
)

async def get_redis():
    async with aioredis.Redis(connection_pool=redis_pool) as client:
        yield client
import os
import redis.asyncio as aioredis
from dotenv import load_dotenv

load_dotenv()

IS_IN_DOCKER = os.path.exists('/.dockerenv')

DEFAULT_REDIS_HOST = os.getenv("REDIS_HOST") if IS_IN_DOCKER else "localhost"

HOST = (DEFAULT_REDIS_HOST)
PORT = os.getenv("REDIS_PORT", "6379")

# Збираємо в URL формат для Redis
REDIS_URL = f"redis://{HOST}:{PORT}/0"

# Ініціалізуємо пул з'єднань
redis_pool = aioredis.ConnectionPool.from_url(REDIS_URL, decode_responses=True)

# Dependency для отримання клієнта Redis
async def get_redis():
    async with aioredis.Redis(connection_pool=redis_pool) as client:
        yield client
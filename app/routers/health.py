from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
import redis.asyncio as aioredis

from app.database.db_postgres import get_db_postgres
from app.database.db_redis import get_db_redis

router = APIRouter()

@router.get(path="/", status_code=status.HTTP_200_OK)
async def health_check(
    db: AsyncSession = Depends(get_db_postgres),
    redis: aioredis.Redis = Depends(get_db_redis)
):
    health_status = {
        "status_code": status.HTTP_200_OK,
        "detail": "ok",
        "result": "working",
        "postgres": "failed",
        "redis": "failed"
    }

    # Перевіряємо PostgreSQL
    try:
        await db.execute(text("SELECT 1"))
        health_status["postgres"] = "working"
    except Exception as e:
        health_status["status_code"] = status.HTTP_500_INTERNAL_SERVER_ERROR
        health_status["detail"] = "error"
        health_status["postgres"] = f"Error: {str(e)}"

    # Перевіряємо Redis
    try:
        await redis.ping()
        health_status["redis"] = "working"
    except Exception as e:
        health_status["status_code"] = status.HTTP_500_INTERNAL_SERVER_ERROR
        health_status["detail"] = "error"
        health_status["redis"] = f"Error: {str(e)}"

    return health_status
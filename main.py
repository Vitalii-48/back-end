import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
import redis.asyncio as aioredis

from app.core.database import get_db
from app.core.redis import get_redis
app = FastAPI()

# Додаємо блок CORS для роботи з фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Дозволяємо запити з будь-яких адрес
    allow_credentials=True,
    allow_methods=["*"],  # Дозволяємо всі методи (GET, POST тощо)
    allow_headers=["*"],  # Дозволяємо всі заголовки
)
@app.get("/")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis)
):
    health_status = {
        "status_code": 200,
        "detail": "ok",
        "postgres": "failed",
        "redis": "failed"
    }

    # 1. Перевіряємо асинхронний Postgres
    try:
        await db.execute(text("SELECT 1"))
        health_status["postgres"] = "working"
    except Exception as e:
        health_status["status_code"] = 500
        health_status["detail"] = "error"
        health_status["postgres"] = f"Error: {str(e)}"

    # 2. Перевіряємо асинхронний Redis
    try:
        # Смикаємо команду ping у нашого клієнта
        await redis.ping()
        health_status["redis"] = "working"
    except Exception as e:
        health_status["status_code"] = 500
        health_status["detail"] = "error"
        health_status["redis"] = f"Error: {str(e)}"

    return health_status



if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
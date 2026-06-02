import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import health  # Імпортуємо наш роутер з першої гілки
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
import redis.asyncio as aioredis

from app.core.database import get_db
from app.core.redis import get_redis
app = FastAPI()

# Чіткий список дозволених локальних адрес для безпеки
ORIGINS = [
    "http://localhost",
    "http://internship.local",
    "http://localhost:3000",
    "http://internship.local:3000",
]

# Додаємо блок CORS для роботи з фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,  # Дозволяємо запити тільки з визначених адрес (безпечний підхід)
    allow_credentials=True,
    allow_methods=["*"],  # Дозволяємо всі методи (GET, POST тощо)
    allow_headers=["*"],  # Дозволяємо всі заголовки
)

# Підключаємо наш роутер (сам ендпоінт живе всередині app/routers/health.py)
app.include_router(health.router)
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import api_router
from app.core.config import settings
from app.core.logger import setup_logger

logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Додаток запущено")
    yield
    logger.info("Додаток зупинено")
app = FastAPI(lifespan=lifespan)

# Додаємо блок CORS для роботи з фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(settings, "CORS_ORIGINS", ["*"]),
    allow_credentials=True,
    allow_methods=["*"],  # Дозволяємо всі методи (GET, POST тощо)
    allow_headers=["*"],  # Дозволяємо всі заголовки
)

# Підключаємо наш роутер
app.include_router(api_router)

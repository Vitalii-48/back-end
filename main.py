from contextlib import asynccontextmanager
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.routers import api_router
from app.core.config import settings
from app.core.logger import setup_logger
from fastapi.responses import JSONResponse


logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Додаток запущено")
    yield
    logger.info("Додаток зупинено")
app = FastAPI(lifespan=lifespan)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print("=== ПОМИЛКА ===")
    print(traceback.format_exc())
    print("===============")
    logger.error(f"Необроблена помилка: {exc}\n{traceback.format_exc()}")
    return JSONResponse(status_code=500, content={"detail": str(exc)})

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

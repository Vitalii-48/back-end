# app/routers/__init__.py
from fastapi import APIRouter
from app.routers import health, auth, users

# 1. Створюємо головний роутер
api_router = APIRouter()

# 2. Об'єднуємо підмодулі
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(auth.me_router)
api_router.include_router(users.router)

# 3. Визначаємо публічний інтерфейс модуля
__all__ = ["api_router"]
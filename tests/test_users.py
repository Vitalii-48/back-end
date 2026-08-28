import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.user_service import UserService
from app.schemas.user import SignUpRequest
from fastapi import HTTPException

@pytest.mark.asyncio
async def test_create_user_success():
    """Тест успішного створення юзера"""
    mock_db = AsyncMock()
    service = UserService(mock_db)

    # Mock (заглушка) — замінюємо реальну БД фейковою
    service.repo.get_by_email = AsyncMock(return_value=None)
    service.repo.create_result = AsyncMock(return_value=MagicMock(
        id=1, username="testuser", email="test@example.com", is_active=True
    ))

    data = SignUpRequest(username="testuser", email="test@example.com", password="secret123")
    user = await service.create_user(data)

    assert user.email == "test@example.com"
    service.repo.create_result.assert_called_once()

@pytest.mark.asyncio
async def test_create_user_duplicate_email():
    """Тест — помилка якщо email вже існує (duplicate — дублікат)"""
    mock_db = AsyncMock()
    service = UserService(mock_db)
    service.repo.get_by_email = AsyncMock(return_value=MagicMock())  # вже існує

    data = SignUpRequest(username="testuser", email="test@example.com", password="secret123")

    with pytest.raises(HTTPException) as exc_info:
        await service.create_user(data)

    assert exc_info.value.status_code == 409

@pytest.mark.asyncio
async def test_get_user_not_found():
    """Тест — 404 якщо юзер не знайдений (not found)"""
    mock_db = AsyncMock()
    service = UserService(mock_db)
    service.repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_user_by_id(999)

    assert exc_info.value.status_code == 404
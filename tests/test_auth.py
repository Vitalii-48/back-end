import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
import bcrypt

from app.services.auth_service import AuthService
from app.schemas.auth import SignInRequest


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def auth_service(mock_db):
    return AuthService(mock_db)


@pytest.mark.asyncio
async def test_sign_in_success(auth_service):
    """Тест успішного входу через email/пароль"""
    hashed = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode()

    mock_user = MagicMock()
    mock_user.id = "some-uuid"
    mock_user.email = "test@test.com"
    mock_user.hashed_password = hashed

    auth_service.user_repo.get_by_email = AsyncMock(return_value=mock_user)

    result = await auth_service.sign_in(
        SignInRequest(email="test@test.com", password="password123")
    )

    assert result.access_token is not None
    assert result.token_type == "bearer"


@pytest.mark.asyncio
async def test_sign_in_wrong_password(auth_service):
    """Тест з невірним паролем"""
    hashed = bcrypt.hashpw(b"correct_password", bcrypt.gensalt()).decode()

    mock_user = MagicMock()
    mock_user.hashed_password = hashed

    auth_service.user_repo.get_by_email = AsyncMock(return_value=mock_user)

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.sign_in(
            SignInRequest(email="test@test.com", password="wrong_password")
        )

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_sign_in_user_not_found(auth_service):
    """Тест коли користувача не існує"""
    auth_service.user_repo.get_by_email = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.sign_in(
            SignInRequest(email="nobody@test.com", password="any")
        )

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_auth0_sign_in_existing_user(auth_service):
    """Тест Auth0 входу з існуючим користувачем"""
    mock_user = MagicMock()
    mock_user.id = "some-uuid"
    mock_user.email = "test@gmail.com"

    auth_service.user_repo.get_by_email = AsyncMock(return_value=mock_user)

    # Mock (заглушка) для verify_auth0_token
    with patch(
        "app.services.auth_service.verify_auth0_token",
        AsyncMock(return_value={"email": "test@gmail.com"})
    ):
        result = await auth_service.auth0_sign_in("fake_token")

    assert result.access_token is not None
    assert result.token_type == "bearer"


@pytest.mark.asyncio
async def test_auth0_sign_in_creates_new_user(auth_service):
    """Тест що Auth0 створює нового користувача якщо його немає в БД"""
    mock_new_user = MagicMock()
    mock_new_user.id = "new-uuid"
    mock_new_user.email = "new@gmail.com"

    # Спочатку користувача немає, потім створюється
    auth_service.user_repo.get_by_email = AsyncMock(return_value=None)
    auth_service.user_repo.create_result = AsyncMock(return_value=mock_new_user)

    with patch(
        "app.services.auth_service.verify_auth0_token",
        AsyncMock(return_value={"email": "new@gmail.com"})
    ):
        result = await auth_service.auth0_sign_in("fake_token")

    assert result.access_token is not None
    auth_service.user_repo.create_result.assert_called_once()


@pytest.mark.asyncio
async def test_auth0_sign_in_no_email(auth_service):
    """Тест що кидає помилку якщо email відсутній в токені"""
    with patch(
        "app.services.auth_service.verify_auth0_token",
        AsyncMock(return_value={})  # Порожній payload без email
    ):
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.auth0_sign_in("fake_token")

    assert exc_info.value.status_code == 400
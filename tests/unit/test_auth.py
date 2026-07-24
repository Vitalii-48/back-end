import pytest
import uuid
import bcrypt
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

from app.models.user import User
from app.services.auth_service import AuthService
from app.schemas.auth import SignInRequest


def make_user(**overrides) -> User:
    """Factory helper — створює User з усіма обов'язковими полями за замовчуванням."""
    defaults = {
        "id": uuid.uuid4(),
        "username": "test_user",
        "email": "test@test.com",
        "hashed_password": bcrypt.hashpw(b"correct_password", bcrypt.gensalt()).decode("utf-8"),
    }
    defaults.update(overrides)
    return User(**defaults)


def make_service() -> AuthService:
    """Створює AuthService з підміненим (mocked) репозиторієм, без реального підключення до БД."""
    svc = object.__new__(AuthService)
    svc.user_repo = AsyncMock()
    return svc


# ---------- sign_in ----------

@pytest.mark.asyncio
async def test_sign_in_user_not_found():
    svc = make_service()
    svc.user_repo.get_by_email.return_value = None
    data = SignInRequest(email="nope@test.com", password="secret123")

    with pytest.raises(HTTPException) as exc_info:
        await svc.sign_in(data)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_sign_in_wrong_password():
    svc = make_service()
    fake_user = make_user()
    svc.user_repo.get_by_email.return_value = fake_user

    data = SignInRequest(email="test@test.com", password="wrong_password")

    with pytest.raises(HTTPException) as exc_info:
        await svc.sign_in(data)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_sign_in_success():
    svc = make_service()
    fake_user = make_user()
    svc.user_repo.get_by_email.return_value = fake_user

    data = SignInRequest(email="test@test.com", password="correct_password")

    with patch("app.services.auth_service.create_access_token", return_value="fake.jwt.token"):
        result = await svc.sign_in(data)

    assert result.access_token == "fake.jwt.token"


# ---------- auth0_sign_in ----------

@pytest.mark.asyncio
async def test_auth0_sign_in_email_missing():
    svc = make_service()

    with patch(
        "app.services.auth_service.verify_auth0_token",
        new=AsyncMock(return_value={}),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await svc.auth0_sign_in("some.token")

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_auth0_sign_in_existing_user():
    svc = make_service()
    existing_user = make_user(email="test@test.com")
    svc.user_repo.get_by_email.return_value = existing_user

    with patch(
        "app.services.auth_service.verify_auth0_token",
        new=AsyncMock(return_value={"email": "test@test.com"}),
    ), patch("app.services.auth_service.create_access_token", return_value="fake.jwt.token"):
        result = await svc.auth0_sign_in("some.token")

    assert result.access_token == "fake.jwt.token"
    svc.user_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_auth0_sign_in_creates_new_user():
    svc = make_service()
    svc.user_repo.get_by_email.return_value = None
    new_user = make_user(username="newuser", email="newuser@test.com")
    svc.user_repo.create.return_value = new_user

    with patch(
        "app.services.auth_service.verify_auth0_token",
        new=AsyncMock(return_value={"email": "newuser@test.com"}),
    ), patch("app.services.auth_service.create_access_token", return_value="fake.jwt.token"):
        result = await svc.auth0_sign_in("some.token")

    assert result.access_token == "fake.jwt.token"
    svc.user_repo.create.assert_called_once()
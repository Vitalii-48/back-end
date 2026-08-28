import uuid
import pytest
from unittest.mock import AsyncMock
from fastapi import HTTPException

from app.models.user import User
from app.services.user_service import UserService
from app.schemas.user import SignUpRequest, UserUpdateRequest


def make_user(**overrides) -> User:
    """Factory helper — створює User з усіма обов'язковими полями."""
    defaults = {
        "id": uuid.uuid4(),
        "username": "test_user",
        "email": "test@test.com",
        "hashed_password": "hashed_password",
        "is_active": True,
    }
    defaults.update(overrides)
    return User(**defaults)


def make_service() -> UserService:
    """Створює UserService з підміненим (mocked) репозиторієм."""
    svc = object.__new__(UserService)
    svc.repo = AsyncMock()
    return svc


# ---------- get_all_users ----------

@pytest.mark.asyncio
async def test_get_all_users():
    svc = make_service()
    fake_users = [make_user()]
    svc.repo.get_all.return_value = (fake_users, 1)

    result, total = await svc.get_all_users(page=1, per_page=10)

    assert result == fake_users
    assert total == 1
    svc.repo.get_all.assert_called_once_with(skip=0, limit=10)


# ---------- get_user_by_id ----------

@pytest.mark.asyncio
async def test_get_user_by_id_found():
    svc = make_service()
    fake_user = make_user()
    svc.repo.get_by_id.return_value = fake_user

    result = await svc.get_user_by_id(fake_user.id)

    assert result == fake_user


@pytest.mark.asyncio
async def test_get_user_by_id_not_found():
    svc = make_service()
    svc.repo.get_by_id.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await svc.get_user_by_id(uuid.uuid4())

    assert exc_info.value.status_code == 404


# ---------- create_user ----------

@pytest.mark.asyncio
async def test_create_user_success():
    svc = make_service()
    svc.repo.get_by_email.return_value = None
    svc.repo.create.return_value = make_user(email="test_eml@test.com")

    data = SignUpRequest(username="test_name", email="test_eml@test.com", password="secret123")
    result = await svc.create_user(data)

    assert result.email == "test_eml@test.com"
    svc.repo.get_by_email.assert_called_once_with("test_eml@test.com")
    svc.repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_user_email_already_exists():
    svc = make_service()
    svc.repo.get_by_email.return_value = make_user(email="test_eml@test.com")

    data = SignUpRequest(username="test_name", email="test_eml@test.com", password="secret123")

    with pytest.raises(HTTPException) as exc_info:
        await svc.create_user(data)

    assert exc_info.value.status_code == 409
    svc.repo.create.assert_not_called()


# ---------- update_user ----------

@pytest.mark.asyncio
async def test_update_user_forbidden():
    svc = make_service()
    target_id = uuid.uuid4()
    current_user = make_user(id=uuid.uuid4())  # Інший ID, ніж target_id

    data = UserUpdateRequest(username="new_name")

    with pytest.raises(HTTPException) as exc_info:
        await svc.update_user(target_id, data, current_user)

    assert exc_info.value.status_code == 403
    svc.repo.get_by_id.assert_not_called()


@pytest.mark.asyncio
async def test_update_user_success():
    svc = make_service()
    existing_user = make_user(hashed_password="old_hash")
    current_user = make_user(id=existing_user.id)

    svc.repo.get_by_id.return_value = existing_user
    svc.repo.update.return_value = existing_user

    data = UserUpdateRequest(username="new_name", password="new_password")
    result = await svc.update_user(existing_user.id, data, current_user)

    assert result.username == "new_name"
    assert result.hashed_password != "old_hash"
    svc.repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_not_found():
    svc = make_service()
    same_id = uuid.uuid4()
    current_user = make_user(id=same_id)

    svc.repo.get_by_id.return_value = None

    data = UserUpdateRequest(username="new_name")

    with pytest.raises(HTTPException) as exc_info:
        await svc.update_user(same_id, data, current_user)

    assert exc_info.value.status_code == 404


# ---------- delete_user ----------

@pytest.mark.asyncio
async def test_delete_user_forbidden():
    svc = make_service()
    target_id = uuid.uuid4()
    current_user = make_user(id=uuid.uuid4())

    with pytest.raises(HTTPException) as exc_info:
        await svc.delete_user(target_id, current_user)

    assert exc_info.value.status_code == 403
    svc.repo.delete.assert_not_called()


@pytest.mark.asyncio
async def test_delete_user_success():
    svc = make_service()
    existing_user = make_user()
    current_user = make_user(id=existing_user.id)

    svc.repo.get_by_id.return_value = existing_user

    await svc.delete_user(existing_user.id, current_user)

    svc.repo.delete.assert_called_once_with(existing_user)


@pytest.mark.asyncio
async def test_delete_user_not_found():
    svc = make_service()
    same_id = uuid.uuid4()
    current_user = make_user(id=same_id)

    svc.repo.get_by_id.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await svc.delete_user(same_id, current_user)

    assert exc_info.value.status_code == 404
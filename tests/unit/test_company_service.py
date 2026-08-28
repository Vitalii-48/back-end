import uuid
import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock
from fastapi import HTTPException

from app.models.company import Company
from app.models.user import User
from app.services.company_service import CompanyService
from app.schemas.company import CompanyCreateRequest, CompanyUpdateRequest


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


def make_company(**overrides) -> Company:
    """Factory helper — створює Company з усіма обов'язковими полями за замовчуванням."""
    defaults = {
        "id": uuid.uuid4(),
        "name": "Test Co",
        "description": "desc",
        "owner_id": uuid.uuid4(),
        "is_visible": True,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return Company(**defaults)


def make_service() -> CompanyService:
    """Створює CompanyService з підміненими (mocked) репозиторіями."""
    svc = object.__new__(CompanyService)
    svc.session = AsyncMock()
    svc.repo = AsyncMock()
    svc.members_repo = AsyncMock()
    return svc


# ---------- create_company ----------

@pytest.mark.asyncio
async def test_create_company_success():
    svc = make_service()
    current_user = make_user()

    fake_company = make_company(owner_id=current_user.id)
    svc.repo.get_company_by_name.return_value = None
    svc.repo.create_company.return_value = fake_company

    data = CompanyCreateRequest(name="Test Co", description="desc")

    result = await svc.create_company(data, current_user)

    assert result.name == "Test Co"
    svc.members_repo.create_member.assert_called_once()
    svc.session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_company_rolls_back_on_error():
    svc = make_service()
    current_user = make_user()

    svc.repo.get_company_by_name.return_value = None
    svc.repo.create_company.side_effect = Exception("db error")

    data = CompanyCreateRequest(name="Test Co", description="desc")

    with pytest.raises(Exception):
        await svc.create_company(data, current_user)

    svc.session.rollback.assert_called_once()


# ---------- get_company ----------

@pytest.mark.asyncio
async def test_get_company_found():
    svc = make_service()
    fake_company = make_company()
    svc.repo.get_company_by_id.return_value = fake_company

    result = await svc.get_company(fake_company.id)

    assert result == fake_company


@pytest.mark.asyncio
async def test_get_company_not_found():
    svc = make_service()
    svc.repo.get_company_by_id.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await svc.get_company(uuid.uuid4())

    assert exc_info.value.status_code == 404


# ---------- update_company ----------

@pytest.mark.asyncio
async def test_update_company_not_found():
    svc = make_service()
    svc.repo.get_company_by_id.return_value = None
    current_user = make_user()

    data = CompanyUpdateRequest(name="New name")

    with pytest.raises(HTTPException) as exc_info:
        await svc.update_company(uuid.uuid4(), data, current_user)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_update_company_forbidden():
    svc = make_service()
    owner_id = uuid.uuid4()
    fake_company = make_company(owner_id=owner_id, name="Old")
    svc.repo.get_company_by_id.return_value = fake_company

    current_user = make_user()  # Генерує власний random UUID, який не дорівнює owner_id

    data = CompanyUpdateRequest(name="New name")

    with pytest.raises(HTTPException) as exc_info:
        await svc.update_company(fake_company.id, data, current_user)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_update_company_success():
    svc = make_service()
    owner_id = uuid.uuid4()
    fake_company = make_company(owner_id=owner_id, name="Old")
    svc.repo.get_company_by_id.return_value = fake_company
    svc.repo.update_company.return_value = fake_company

    current_user = make_user(id=owner_id)  # Вказуємо той самий owner_id

    data = CompanyUpdateRequest(name="New name")

    result = await svc.update_company(fake_company.id, data, current_user)

    assert result.name == "New name"
    svc.repo.update_company.assert_called_once()


# ---------- get_all_companies ----------

@pytest.mark.asyncio
async def test_get_all_companies():
    svc = make_service()
    fake_company = make_company()
    svc.repo.get_all_companies.return_value = ([fake_company], 1)

    result = await svc.get_all_companies(page=1, per_page=10)

    assert result.total == 1
    assert len(result.companies) == 1
    svc.repo.get_all_companies.assert_called_once_with(skip=0, limit=10)


# ---------- delete_company ----------

@pytest.mark.asyncio
async def test_delete_company_not_found():
    svc = make_service()
    svc.repo.get_company_by_id.return_value = None
    current_user = make_user()

    with pytest.raises(HTTPException) as exc_info:
        await svc.delete_company(uuid.uuid4(), current_user)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_company_forbidden():
    svc = make_service()
    owner_id = uuid.uuid4()
    fake_company = make_company(owner_id=owner_id)
    svc.repo.get_company_by_id.return_value = fake_company

    current_user = make_user()  # Не є власником (інший id)

    with pytest.raises(HTTPException) as exc_info:
        await svc.delete_company(fake_company.id, current_user)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_delete_company_success():
    svc = make_service()
    owner_id = uuid.uuid4()
    fake_company = make_company(owner_id=owner_id)
    svc.repo.get_company_by_id.return_value = fake_company

    current_user = make_user(id=owner_id)

    await svc.delete_company(fake_company.id, current_user)

    svc.repo.delete_company.assert_called_once_with(fake_company)
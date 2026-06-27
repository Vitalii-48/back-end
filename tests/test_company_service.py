# app/tests/test_company_service.py
import pytest
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock
from app.services.company_service import CompanyService
from app.schemas.company import CompanyCreateRequest, CompanyUpdateRequest
from app.models.company import Company
from app.models.user import User
from fastapi import HTTPException


def make_user(user_id: UUID) -> User:
    user = MagicMock(spec=User)
    user.id = user_id
    return user


def make_company(company_id: UUID, owner_id: UUID) -> Company:
    company = MagicMock(spec=Company)
    company.id = company_id
    company.owner_id = owner_id
    company.name = "Test Company"
    company.description = "desc"
    company.is_visible = True
    return company


@pytest.fixture
def service():
    session = AsyncMock()
    svc = CompanyService(session)
    svc.repo = AsyncMock()
    return svc


@pytest.mark.asyncio
async def test_create_company(service):
    user_id = uuid4()
    user = make_user(user_id)
    company = make_company(uuid4(), user_id)

    service.repo.create_company = AsyncMock(return_value=company)

    data = CompanyCreateRequest(name="Test Company", is_visible=True)
    result = await service.create_company(data, user)

    service.repo.create_company.assert_called_once()
    assert result.id == company.id
    assert result.name == company.name
    assert result.owner_id == company.owner_id
    assert result.is_visible == company.is_visible


@pytest.mark.asyncio
async def test_get_company_not_found(service):
    service.repo.get_company_by_id = AsyncMock(return_value=None)

    company_id = uuid4()
    with pytest.raises(HTTPException) as exc:
        await service.get_company(company_id)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_company_success(service):
    user_id = uuid4()
    company_id = uuid4()

    user = make_user(user_id)
    company = make_company(company_id, owner_id=user_id)

    service.repo.get_company_by_id = AsyncMock(return_value=company)
    service.repo.update_company = AsyncMock(return_value=company)

    data = CompanyUpdateRequest(name="Updated Name", description="New desc")
    result = await service.update_company(company_id, data, user)

    service.repo.update_company.assert_called_once()
    assert result.name == "Updated Name"
    assert result.description == "New desc"

@pytest.mark.asyncio
async def test_update_company_forbidden(service):
    owner_id = uuid4()
    stranger_id = uuid4()
    company_id = uuid4()

    company = make_company(company_id, owner_id=owner_id)  # власник — один user
    service.repo.get_company_by_id = AsyncMock(return_value=company)

    user = make_user(stranger_id)  # не власник намагається оновити
    data = CompanyUpdateRequest(name="New name", description=None)

    with pytest.raises(HTTPException) as exc:
        await service.update_company(company_id, data, user)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_delete_company_forbidden(service):
    owner_id = uuid4()
    stranger_id = uuid4()
    company_id = uuid4()

    company = make_company(company_id, owner_id=owner_id)
    service.repo.get_company_by_id = AsyncMock(return_value=company)

    user = make_user(stranger_id)
    with pytest.raises(HTTPException) as exc:
        await service.delete_company(company_id, user)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_delete_company_success(service):
    user_id = uuid4()
    company_id = uuid4()

    user = make_user(user_id)
    company = make_company(company_id, owner_id=user_id)

    service.repo.get_company_by_id = AsyncMock(return_value=company)
    service.repo.delete_company = AsyncMock()

    await service.delete_company(company_id, user)
    service.repo.delete_company.assert_called_once_with(company)
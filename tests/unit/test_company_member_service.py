import uuid
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.models.enums import CompanyRole
from app.models.user import User
from app.services.company_member_service import CompanyMemberService


def make_user(**overrides) -> User:
    """Factory helper — створює User з усіма обов'язковими полями за замовчуванням."""
    defaults = {
        "id": uuid.uuid4(),
        "username": "test_user",
        "email": "test@test.com",
        "hashed_password": "hashed_password",
        "is_active": True,
    }
    defaults.update(overrides)
    return User(**defaults)


def make_member(**overrides):
    """Factory helper — створює CompanyMember-подібний об'єкт з усіма полями за замовчуванням."""
    defaults = {
        "id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "company_id": uuid.uuid4(),
        "role": CompanyRole.MEMBER,
        "created_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


def make_service(company_exists=True) -> CompanyMemberService:
    """Створює CompanyMemberService з підміненими (mocked) репозиторіями."""
    svc = object.__new__(CompanyMemberService)
    svc.member_repo = AsyncMock()
    svc.company_repo = AsyncMock()

    if company_exists:
        svc.company_repo.get_company_by_id.return_value = MagicMock(id=uuid.uuid4(), owner_id=uuid.uuid4())
    else:
        svc.company_repo.get_company_by_id.return_value = None

    return svc


# ---------- create_owner_membership ----------

@pytest.mark.asyncio
async def test_create_owner_membership():
    svc = make_service()
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    svc.member_repo.create_membership.return_value = make_member(
        company_id=company_id, user_id=user_id, role=CompanyRole.OWNER
    )

    result = await svc.create_owner_membership(company_id, user_id)

    assert result.role == CompanyRole.OWNER
    svc.member_repo.create_membership.assert_called_once()


# ---------- get_members ----------

@pytest.mark.asyncio
async def test_get_members():
    svc = make_service()
    fake_member = make_member()
    svc.member_repo.get_members_by_company.return_value = ([fake_member], 1)

    result = await svc.get_members(uuid.uuid4(), page=1, per_page=10)

    assert result.total == 1


# ---------- remove_member ----------

@pytest.mark.asyncio
async def test_remove_member_company_not_found():
    svc = make_service(company_exists=False)
    current_user = make_user()

    with pytest.raises(HTTPException) as exc_info:
        await svc.remove_member(uuid.uuid4(), uuid.uuid4(), current_user)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_remove_member_forbidden():
    svc = make_service()
    owner_id = uuid.uuid4()
    company = MagicMock(id=uuid.uuid4(), owner_id=owner_id)
    svc.company_repo.get_company_by_id.return_value = company

    current_user = make_user()  # не owner

    with pytest.raises(HTTPException) as exc_info:
        await svc.remove_member(company.id, uuid.uuid4(), current_user)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_remove_member_cannot_remove_owner():
    svc = make_service()
    owner_id = uuid.uuid4()
    company = MagicMock(id=uuid.uuid4(), owner_id=owner_id)
    svc.company_repo.get_company_by_id.return_value = company

    current_user = make_user(id=owner_id)

    with pytest.raises(HTTPException) as exc_info:
        await svc.remove_member(company.id, owner_id, current_user)

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_remove_member_membership_not_found():
    svc = make_service()
    owner_id = uuid.uuid4()
    company = MagicMock(id=uuid.uuid4(), owner_id=owner_id)
    svc.company_repo.get_company_by_id.return_value = company
    svc.member_repo.get_membership_by_company_and_user.return_value = None

    current_user = make_user(id=owner_id)

    with pytest.raises(HTTPException) as exc_info:
        await svc.remove_member(company.id, uuid.uuid4(), current_user)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_remove_member_success():
    svc = make_service()
    owner_id = uuid.uuid4()
    target_user_id = uuid.uuid4()
    company = MagicMock(id=uuid.uuid4(), owner_id=owner_id)
    svc.company_repo.get_company_by_id.return_value = company

    fake_membership = make_member(company_id=company.id, user_id=target_user_id, role=CompanyRole.MEMBER)
    svc.member_repo.get_membership_by_company_and_user.return_value = fake_membership

    current_user = make_user(id=owner_id)

    await svc.remove_member(company.id, target_user_id, current_user)

    svc.member_repo.delete_membership.assert_called_once_with(fake_membership)


# ---------- leave_company ----------

@pytest.mark.asyncio
async def test_leave_company_not_found():
    svc = make_service(company_exists=False)
    current_user = make_user()

    with pytest.raises(HTTPException) as exc_info:
        await svc.leave_company(uuid.uuid4(), current_user)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_leave_company_owner_cannot_leave():
    svc = make_service()
    owner_id = uuid.uuid4()
    company = MagicMock(id=uuid.uuid4(), owner_id=owner_id)
    svc.company_repo.get_company_by_id.return_value = company

    current_user = make_user(id=owner_id)

    with pytest.raises(HTTPException) as exc_info:
        await svc.leave_company(company.id, current_user)

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_leave_company_membership_not_found():
    svc = make_service()
    company = MagicMock(id=uuid.uuid4(), owner_id=uuid.uuid4())
    svc.company_repo.get_company_by_id.return_value = company
    svc.member_repo.get_membership_by_company_and_user.return_value = None

    current_user = make_user()

    with pytest.raises(HTTPException) as exc_info:
        await svc.leave_company(company.id, current_user)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_leave_company_success():
    svc = make_service()
    company = MagicMock(id=uuid.uuid4(), owner_id=uuid.uuid4())
    svc.company_repo.get_company_by_id.return_value = company

    current_user = make_user()
    fake_membership = make_member(company_id=company.id, user_id=current_user.id, role=CompanyRole.MEMBER)
    svc.member_repo.get_membership_by_company_and_user.return_value = fake_membership

    await svc.leave_company(company.id, current_user)

    svc.member_repo.delete_membership.assert_called_once_with(fake_membership)


# ---------- change_role ----------

@pytest.mark.asyncio
async def test_change_role_success_make_admin():
    svc = make_service()
    company_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    member_id = uuid.uuid4()

    owner = make_member(user_id=owner_id, company_id=company_id, role=CompanyRole.OWNER)
    target = make_member(user_id=member_id, company_id=company_id, role=CompanyRole.MEMBER)

    async def get_member(_c_id, u_id):
        return owner if u_id == owner_id else target

    svc.member_repo.get_membership_by_company_and_user.side_effect = get_member
    svc.member_repo.update_member_role.return_value = make_member(
        user_id=member_id, company_id=company_id, role=CompanyRole.ADMIN
    )

    result = await svc.change_role(company_id, member_id, CompanyRole.ADMIN, make_user(id=owner_id))

    assert result.role == CompanyRole.ADMIN
    svc.member_repo.update_member_role.assert_called_once_with(target, CompanyRole.ADMIN)


@pytest.mark.asyncio
async def test_change_role_company_not_found():
    svc = make_service(company_exists=False)

    with pytest.raises(HTTPException) as exc_info:
        await svc.change_role(uuid.uuid4(), uuid.uuid4(), CompanyRole.ADMIN, make_user())

    assert exc_info.value.status_code == 404
    svc.member_repo.get_membership_by_company_and_user.assert_not_called()


@pytest.mark.asyncio
async def test_change_role_forbidden_for_non_owner():
    svc = make_service()
    company_id = uuid.uuid4()
    requester_id = uuid.uuid4()
    target_id = uuid.uuid4()

    requester = make_member(user_id=requester_id, company_id=company_id, role=CompanyRole.MEMBER)
    target = make_member(user_id=target_id, company_id=company_id, role=CompanyRole.MEMBER)

    async def get_member(_c_id, u_id):
        return requester if u_id == requester_id else target

    svc.member_repo.get_membership_by_company_and_user.side_effect = get_member

    with pytest.raises(HTTPException) as exc_info:
        await svc.change_role(company_id, target_id, CompanyRole.ADMIN, make_user(id=requester_id))

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_change_role_target_not_member():
    svc = make_service()
    company_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    stranger_id = uuid.uuid4()

    owner = make_member(user_id=owner_id, company_id=company_id, role=CompanyRole.OWNER)

    async def get_member(_c_id, u_id):
        return owner if u_id == owner_id else None

    svc.member_repo.get_membership_by_company_and_user.side_effect = get_member

    with pytest.raises(HTTPException) as exc_info:
        await svc.change_role(company_id, stranger_id, CompanyRole.ADMIN, make_user(id=owner_id))

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_change_role_cannot_change_owner_role():
    svc = make_service()
    company_id = uuid.uuid4()
    owner_id = uuid.uuid4()

    owner = make_member(user_id=owner_id, company_id=company_id, role=CompanyRole.OWNER)
    svc.member_repo.get_membership_by_company_and_user.return_value = owner

    with pytest.raises(HTTPException) as exc_info:
        await svc.change_role(company_id, owner_id, CompanyRole.ADMIN, make_user(id=owner_id))

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_change_role_already_has_role():
    svc = make_service()
    company_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    admin_id = uuid.uuid4()

    owner = make_member(user_id=owner_id, company_id=company_id, role=CompanyRole.OWNER)
    already_admin = make_member(user_id=admin_id, company_id=company_id, role=CompanyRole.ADMIN)

    async def get_member(_c_id, u_id):
        return owner if u_id == owner_id else already_admin

    svc.member_repo.get_membership_by_company_and_user.side_effect = get_member

    with pytest.raises(HTTPException) as exc_info:
        await svc.change_role(company_id, admin_id, CompanyRole.ADMIN, make_user(id=owner_id))

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_change_role_success_remove_admin():
    svc = make_service()
    company_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    admin_id = uuid.uuid4()

    owner = make_member(user_id=owner_id, company_id=company_id, role=CompanyRole.OWNER)
    admin = make_member(user_id=admin_id, company_id=company_id, role=CompanyRole.ADMIN)

    async def get_member(_c_id, u_id):
        return owner if u_id == owner_id else admin

    svc.member_repo.get_membership_by_company_and_user.side_effect = get_member
    svc.member_repo.update_member_role.return_value = make_member(
        user_id=admin_id, company_id=company_id, role=CompanyRole.MEMBER
    )

    result = await svc.change_role(company_id, admin_id, CompanyRole.MEMBER, make_user(id=owner_id))

    assert result.role == CompanyRole.MEMBER
    svc.member_repo.update_member_role.assert_called_once_with(admin, CompanyRole.MEMBER)


# ---------- get_admins ----------

@pytest.mark.asyncio
async def test_get_admins_company_not_found():
    svc = make_service(company_exists=False)

    with pytest.raises(HTTPException) as exc_info:
        await svc.get_admins(uuid.uuid4(), make_user())

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_admins_forbidden_not_member():
    svc = make_service()
    company = MagicMock(id=uuid.uuid4(), owner_id=uuid.uuid4())
    svc.company_repo.get_company_by_id.return_value = company
    svc.member_repo.get_membership_by_company_and_user.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await svc.get_admins(company.id, make_user())

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_admins_returns_list():
    svc = make_service()
    company_id = uuid.uuid4()
    requester = make_user()

    company = MagicMock(id=company_id, owner_id=uuid.uuid4())
    svc.company_repo.get_company_by_id.return_value = company
    svc.member_repo.get_membership_by_company_and_user.return_value = make_member(
        user_id=requester.id, company_id=company_id, role=CompanyRole.MEMBER
    )

    admins = [
        make_member(company_id=company_id, role=CompanyRole.ADMIN),
        make_member(company_id=company_id, role=CompanyRole.ADMIN),
    ]
    svc.member_repo.get_admins_by_company_id.return_value = (admins, len(admins))

    result = await svc.get_admins(company_id, requester, offset=0, limit=10)

    assert result.total == 2
    assert len(result.admins) == 2
    svc.member_repo.get_admins_by_company_id.assert_called_once_with(company_id, 0, 10)
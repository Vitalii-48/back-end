# tests/test_company_member_service.py
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from datetime import datetime, UTC

from app.models.enums import CompanyRole
from app.models.user import User
from app.services.company_member_service import CompanyMemberService


class FakeMember:
    def __init__(self, user_id, company_id, role):
        self.id = uuid.uuid4()
        self.user_id = user_id
        self.company_id = company_id
        self.role = role
        self.created_at = datetime.now(UTC)



class FakeUser(User):
    def __init__(self, user_id):
        super().__init__(id=user_id)


def make_service(company_exists=True):
    """
    Створює CompanyMemberService з підміненими (mocked) репозиторіями,
    без реального підключення до БД.
    """
    svc = object.__new__(CompanyMemberService)
    svc.session = AsyncMock()
    svc.member_repo = AsyncMock()
    svc.company_repo = AsyncMock()

    if company_exists:
        svc.company_repo.get_company_by_id.return_value = MagicMock(id=uuid.uuid4())
    else:
        svc.company_repo.get_company_by_id.return_value = None

    return svc


@pytest.mark.asyncio
async def test_make_admin_success():
    """Owner успішно призначає звичайного учасника адміном."""
    company_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    member_id = uuid.uuid4()

    owner = FakeMember(owner_id, company_id, CompanyRole.OWNER)
    target = FakeMember(member_id, company_id, CompanyRole.MEMBER)

    svc = make_service()

    async def get_member(c_id, u_id):
        if u_id == owner_id:
            return owner
        return target

    svc.member_repo.get_membership_by_company_and_user.side_effect = get_member
    svc.member_repo.update_member_role.return_value = FakeMember(
        member_id, company_id, CompanyRole.ADMIN
    )

    result = await svc.change_role(
        company_id, member_id, CompanyRole.ADMIN, FakeUser(owner_id)
    )
    assert result.role == CompanyRole.ADMIN
    svc.member_repo.update_member_role.assert_called_once_with(target, CompanyRole.ADMIN)


@pytest.mark.asyncio
async def test_make_admin_company_not_found():
    """Якщо компанія не існує — 404, до перевірки прав справа не доходить."""
    svc = make_service(company_exists=False)

    with pytest.raises(HTTPException) as exc_info:
        await svc.change_role(uuid.uuid4(), uuid.uuid4(), CompanyRole.ADMIN, FakeUser(uuid.uuid4()))

    assert exc_info.value.status_code == 404
    svc.member_repo.get_membership_by_company_and_user.assert_not_called()


@pytest.mark.asyncio
async def test_make_admin_forbidden_for_non_owner():
    """Звичайний Member не може призначати адмінів — 403."""
    company_id = uuid.uuid4()
    requester_id = uuid.uuid4()
    target_id = uuid.uuid4()

    requester = FakeMember(requester_id, company_id, CompanyRole.MEMBER)
    target = FakeMember(target_id, company_id, CompanyRole.MEMBER)

    svc = make_service()

    async def get_member(c_id, u_id):
        if u_id == requester_id:
            return requester
        return target

    svc.member_repo.get_membership_by_company_and_user.side_effect = get_member

    with pytest.raises(HTTPException) as exc_info:
        await svc.change_role(company_id, target_id, CompanyRole.ADMIN, FakeUser(requester_id))

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_make_admin_target_not_member():
    """Якщо цільовий юзер не є учасником компанії — 404."""
    company_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    stranger_id = uuid.uuid4()

    owner = FakeMember(owner_id, company_id, CompanyRole.OWNER)

    svc = make_service()

    async def get_member(c_id, u_id):
        if u_id == owner_id:
            return owner
        return None  # stranger не є учасником

    svc.member_repo.get_membership_by_company_and_user.side_effect = get_member

    with pytest.raises(HTTPException) as exc_info:
        await svc.change_role(company_id, stranger_id, CompanyRole.ADMIN, FakeUser(owner_id))

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_make_admin_cannot_change_owner_role():
    """Не можна змінити роль Owner-а — 400."""
    company_id = uuid.uuid4()
    owner_id = uuid.uuid4()

    owner = FakeMember(owner_id, company_id, CompanyRole.OWNER)

    svc = make_service()
    svc.member_repo.get_membership_by_company_and_user.return_value = owner

    with pytest.raises(HTTPException) as exc_info:
        await svc.change_role(company_id, owner_id, CompanyRole.ADMIN, FakeUser(owner_id))
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_make_admin_already_admin():
    """Якщо юзер вже адмін — повторне призначення дає 400."""
    company_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    admin_id = uuid.uuid4()

    owner = FakeMember(owner_id, company_id, CompanyRole.OWNER)
    already_admin = FakeMember(admin_id, company_id, CompanyRole.ADMIN)

    svc = make_service()

    async def get_member(c_id, u_id):
        if u_id == owner_id:
            return owner
        return already_admin

    svc.member_repo.get_membership_by_company_and_user.side_effect = get_member

    with pytest.raises(HTTPException) as exc_info:
        await svc.change_role(company_id, admin_id, CompanyRole.ADMIN, FakeUser(owner_id))
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_remove_admin_success():
    """Owner успішно знімає роль адміна — учасник стає звичайним Member."""
    company_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    admin_id = uuid.uuid4()

    owner = FakeMember(owner_id, company_id, CompanyRole.OWNER)
    admin = FakeMember(admin_id, company_id, CompanyRole.ADMIN)

    svc = make_service()

    async def get_member(c_id, u_id):
        if u_id == owner_id:
            return owner
        return admin

    svc.member_repo.get_membership_by_company_and_user.side_effect = get_member
    svc.member_repo.update_member_role.return_value = FakeMember(
        admin_id, company_id, CompanyRole.MEMBER
    )

    result = await svc.change_role(
        company_id, admin_id, CompanyRole.MEMBER, FakeUser(owner_id)
    )
    assert result.role == CompanyRole.MEMBER
    svc.member_repo.update_member_role.assert_called_once_with(admin, CompanyRole.MEMBER)


@pytest.mark.asyncio
async def test_remove_admin_user_not_admin():
    """Якщо знімаємо адмінку з того, хто не адмін — 400."""
    company_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    member_id = uuid.uuid4()

    owner = FakeMember(owner_id, company_id, CompanyRole.OWNER)
    plain = FakeMember(member_id, company_id, CompanyRole.MEMBER)

    svc = make_service()

    async def get_member(c_id, u_id):
        if u_id == owner_id:
            return owner
        return plain

    svc.member_repo.get_membership_by_company_and_user.side_effect = get_member

    with pytest.raises(HTTPException) as exc_info:
        await svc.change_role(company_id, member_id, CompanyRole.MEMBER, FakeUser(owner_id))
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_get_admins_returns_list():
    """get_admins повертає список адмінів від репозиторію."""
    company_id = uuid.uuid4()
    admins = [
        FakeMember(uuid.uuid4(), company_id, CompanyRole.ADMIN),
        FakeMember(uuid.uuid4(), company_id, CompanyRole.ADMIN),
    ]

    svc = make_service()
    svc.member_repo.get_admins_by_company_id.return_value = (admins, len(admins))

    result = await svc.get_admins(company_id, offset=0, limit=10)

    assert result.total == 2
    assert len(result.admins) == 2
    svc.member_repo.get_admins_by_company_id.assert_called_once_with(company_id, 0, 10)


@pytest.mark.asyncio
async def test_get_admins_company_not_found():
    """get_admins для неіснуючої компанії — 404."""
    svc = make_service(company_exists=False)

    with pytest.raises(HTTPException) as exc_info:
        await svc.get_admins(uuid.uuid4())

    assert exc_info.value.status_code == 404
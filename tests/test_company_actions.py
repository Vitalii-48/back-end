import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import HTTPException

from app.models.enums import RequestStatus, RequestType, CompanyRole
from app.services.company_request_service import CompanyRequestService
from app.services.company_member_service import CompanyMemberService

# ─── Helpers (допоміжні функції) ────────────────────────────────────────────
def make_user(user_id=None):
    user = MagicMock()
    user.id = user_id or uuid4()
    return user


def make_company(company_id=None, owner_id=None):
    company = MagicMock()
    company.id = company_id or uuid4()
    company.owner_id = owner_id or uuid4()
    return company


def make_request(request_id=None, company_id=None, user_id=None, request_type=RequestType.INVITE):
    request = MagicMock()
    request.id = request_id or uuid4()
    request.company_id = company_id or uuid4()
    request.user_id = user_id or uuid4()
    request.type = request_type
    request.status = RequestStatus.PENDING
    return request


# ─── Tests: owner invite ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_owner_can_invite_user():
    service = CompanyRequestService(AsyncMock())
    service.repo = AsyncMock()
    service.member_repo = AsyncMock()
    service.company_repo = AsyncMock()

    owner = make_user()
    company = make_company(owner_id=owner.id)
    invited_user_id = uuid4()

    service.company_repo.get_company_by_id.return_value = company
    service.member_repo.get_membership_by_company_and_user.return_value = None
    service.repo.get_pending_request.return_value = None

    created_request = make_request(
        company_id=company.id,
        user_id=invited_user_id,
        request_type=RequestType.INVITE,
    )
    service.repo.create_request.return_value = created_request

    result = await service.invite_user(company.id, invited_user_id, owner)

    assert result.user_id == invited_user_id
    assert result.type == RequestType.INVITE
    service.repo.create_request.assert_called_once()


# ─── Tests: не-owner не може invite ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_non_owner_cannot_invite_user():
    service = CompanyRequestService(AsyncMock())
    service.company_repo = AsyncMock()

    owner_id = uuid4()
    stranger = make_user()
    company = make_company(owner_id=owner_id)

    service.company_repo.get_company_by_id.return_value = company

    with pytest.raises(HTTPException) as exc:
        await service.invite_user(company.id, uuid4(), stranger)

    assert exc.value.status_code == 403


# ─── Tests: user request to join ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_user_can_request_to_join_company():
    service = CompanyRequestService(AsyncMock())
    service.repo = AsyncMock()
    service.member_repo = AsyncMock()
    service.company_repo = AsyncMock()

    user = make_user()
    company = make_company()

    service.company_repo.get_company_by_id.return_value = company
    service.member_repo.get_membership_by_company_and_user.return_value = None
    service.repo.get_pending_request.return_value = None

    created_request = make_request(
        company_id=company.id,
        user_id=user.id,
        request_type=RequestType.REQUEST,
    )
    service.repo.create_request.return_value = created_request

    result = await service.request_to_join(company.id, user)

    assert result.user_id == user.id
    assert result.type == RequestType.REQUEST
    service.repo.create_request.assert_called_once()


# ─── Tests: accept invitation ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_user_accepts_invitation_and_becomes_member():
    service = CompanyRequestService(AsyncMock())
    service.repo = AsyncMock()
    service.member_repo = AsyncMock()

    user = make_user()
    invitation = make_request(user_id=user.id, request_type=RequestType.INVITE)

    service.repo.get_request_by_id.return_value = invitation
    service.repo.update_request.return_value = invitation

    membership = MagicMock()
    membership.company_id = invitation.company_id
    membership.user_id = user.id
    membership.role = CompanyRole.MEMBER
    service.member_repo.create_membership.return_value = membership

    await service.accept_invitation(invitation.id, user)

    assert invitation.status == RequestStatus.ACCEPTED
    service.member_repo.create_membership.assert_called_once()


# ─── Tests: owner accepts join request ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_owner_accepts_join_request_and_user_becomes_member():
    service = CompanyRequestService(AsyncMock())
    service.repo = AsyncMock()
    service.member_repo = AsyncMock()
    service.company_repo = AsyncMock()

    owner = make_user()
    company = make_company(owner_id=owner.id)
    join_request = make_request(
        company_id=company.id,
        user_id=uuid4(),
        request_type=RequestType.REQUEST,
    )

    service.repo.get_request_by_id.return_value = join_request
    service.company_repo.get_company_by_id.return_value = company
    service.repo.update_request.return_value = join_request
    service.member_repo.create_membership.return_value = MagicMock()

    await service.accept_join_request(join_request.id, owner)

    assert join_request.status == RequestStatus.ACCEPTED
    service.member_repo.create_membership.assert_called_once()


# ─── Tests: remove member ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_owner_can_remove_member():
    service = CompanyMemberService(AsyncMock())
    service.repo = AsyncMock()
    service.company_repo = AsyncMock()

    owner = make_user()
    member_id = uuid4()
    company = make_company(owner_id=owner.id)
    membership = MagicMock()
    membership.user_id = member_id

    service.company_repo.get_company_by_id.return_value = company
    service.repo.get_membership_by_company_and_user.return_value = membership

    await service.remove_member(company.id, member_id, owner)

    service.repo.delete_membership.assert_called_once_with(membership)


# ─── Tests: user leaves company ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_user_can_leave_company():
    service = CompanyMemberService(AsyncMock())
    service.repo = AsyncMock()
    service.company_repo = AsyncMock()

    owner_id = uuid4()
    user = make_user()
    company = make_company(owner_id=owner_id)
    membership = MagicMock()
    membership.user_id = user.id

    service.company_repo.get_company_by_id.return_value = company
    service.repo.get_membership_by_company_and_user.return_value = membership

    await service.leave_company(company.id, user)

    service.repo.delete_membership.assert_called_once_with(membership)


# ─── Tests: owner cannot leave ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_owner_cannot_leave_own_company():
    service = CompanyMemberService(AsyncMock())
    service.company_repo = AsyncMock()

    owner = make_user()
    company = make_company(owner_id=owner.id)

    service.company_repo.get_company_by_id.return_value = company

    with pytest.raises(HTTPException) as exc:
        await service.leave_company(company.id, owner)

    assert exc.value.status_code == 400
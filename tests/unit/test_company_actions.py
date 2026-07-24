import uuid
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.models.enums import CompanyRole, RequestStatus, RequestType
from app.models.user import User
from app.services.company_request_service import CompanyRequestService


# ─── Helpers (допоміжні функції) ────────────────────────────────────────────

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


def make_company(company_id=None, owner_id=None):
    """Factory helper — створює MagicMock компанії."""
    company = MagicMock()
    company.id = company_id or uuid.uuid4()
    company.owner_id = owner_id or uuid.uuid4()
    return company


def make_request(request_id=None, company_id=None, user_id=None, request_type=RequestType.INVITE):
    """Factory helper — створює MagicMock запиту/запрошення."""
    request = MagicMock()
    request.id = request_id or uuid.uuid4()
    request.company_id = company_id or uuid.uuid4()
    request.user_id = user_id or uuid.uuid4()
    request.type = request_type
    request.status = RequestStatus.PENDING
    request.created_at = datetime.now(UTC)
    return request


def make_service() -> CompanyRequestService:
    """Створює CompanyRequestService з підміненими (mocked) репозиторіями."""
    svc = object.__new__(CompanyRequestService)
    svc.repo = AsyncMock()
    svc.member_repo = AsyncMock()
    svc.company_repo = AsyncMock()
    return svc


# ============================================================
# invite_user
# ============================================================

class TestInviteUser:

    @pytest.mark.asyncio
    async def test_invite_user_success(self):
        svc = make_service()
        owner = make_user()
        company = make_company(owner_id=owner.id)
        invited_user_id = uuid.uuid4()

        svc.company_repo.get_company_by_id.return_value = company
        svc.member_repo.get_membership_by_company_and_user.return_value = None
        svc.repo.get_pending_request.return_value = None

        created_request = make_request(
            company_id=company.id,
            user_id=invited_user_id,
            request_type=RequestType.INVITE,
        )
        svc.repo.create_request.return_value = created_request

        result = await svc.invite_user(company.id, invited_user_id, owner)

        assert result.user_id == invited_user_id
        assert result.type == RequestType.INVITE
        svc.repo.create_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_invite_user_forbidden_not_owner(self):
        svc = make_service()
        owner_id = uuid.uuid4()
        stranger = make_user()
        company = make_company(owner_id=owner_id)

        svc.company_repo.get_company_by_id.return_value = company

        with pytest.raises(HTTPException) as exc:
            await svc.invite_user(company.id, uuid.uuid4(), stranger)

        assert exc.value.status_code == 403


# ============================================================
# request_to_join
# ============================================================

class TestRequestToJoin:

    @pytest.mark.asyncio
    async def test_request_to_join_success(self):
        svc = make_service()
        user = make_user()
        company = make_company()

        svc.company_repo.get_company_by_id.return_value = company
        svc.member_repo.get_membership_by_company_and_user.return_value = None
        svc.repo.get_pending_request.return_value = None

        created_request = make_request(
            company_id=company.id,
            user_id=user.id,
            request_type=RequestType.REQUEST,
        )
        svc.repo.create_request.return_value = created_request

        result = await svc.request_to_join(company.id, user)

        assert result.user_id == user.id
        assert result.type == RequestType.REQUEST
        svc.repo.create_request.assert_called_once()


# ============================================================
# accept_invitation
# ============================================================

class TestAcceptInvitation:

    @pytest.mark.asyncio
    async def test_accept_invitation_success(self):
        svc = make_service()
        user = make_user()
        invitation = make_request(user_id=user.id, request_type=RequestType.INVITE)

        svc.repo.get_request_by_id.return_value = invitation
        svc.repo.update_request.return_value = invitation

        membership = MagicMock()
        membership.company_id = invitation.company_id
        membership.user_id = user.id
        membership.role = CompanyRole.MEMBER
        svc.member_repo.create_membership.return_value = membership

        await svc.accept_invitation(invitation.id, user)

        assert invitation.status == RequestStatus.ACCEPTED
        svc.member_repo.create_membership.assert_called_once()


# ============================================================
# decline_invitation
# ============================================================

class TestDeclineInvitation:

    @pytest.mark.asyncio
    async def test_decline_invitation_success(self):
        svc = make_service()
        user = make_user()
        invitation = make_request(user_id=user.id, request_type=RequestType.INVITE)

        svc.repo.get_request_by_id.return_value = invitation
        svc.repo.update_request.return_value = invitation

        await svc.decline_invitation(invitation.id, user)

        assert invitation.status == RequestStatus.DECLINED
        svc.repo.update_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_decline_invitation_not_found(self):
        svc = make_service()
        svc.repo.get_request_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            await svc.decline_invitation(uuid.uuid4(), make_user())

        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_decline_invitation_forbidden_wrong_user(self):
        svc = make_service()
        invitation = make_request(user_id=uuid.uuid4(), request_type=RequestType.INVITE)
        svc.repo.get_request_by_id.return_value = invitation

        with pytest.raises(HTTPException) as exc:
            await svc.decline_invitation(invitation.id, make_user())  # інший user_id

        assert exc.value.status_code == 403


# ============================================================
# cancel_join_request
# ============================================================

class TestCancelJoinRequest:

    @pytest.mark.asyncio
    async def test_cancel_join_request_success(self):
        svc = make_service()
        user = make_user()
        join_request = make_request(user_id=user.id, request_type=RequestType.REQUEST)

        svc.repo.get_request_by_id.return_value = join_request
        svc.repo.update_request.return_value = join_request

        await svc.cancel_join_request(join_request.id, user)

        assert join_request.status == RequestStatus.CANCELED
        svc.repo.update_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_join_request_already_resolved(self):
        svc = make_service()
        user = make_user()
        join_request = make_request(user_id=user.id, request_type=RequestType.REQUEST)
        join_request.status = RequestStatus.ACCEPTED  # вже не PENDING

        svc.repo.get_request_by_id.return_value = join_request

        with pytest.raises(HTTPException) as exc:
            await svc.cancel_join_request(join_request.id, user)

        assert exc.value.status_code == 400


# ============================================================
# cancel_invitation (Owner)
# ============================================================

class TestCancelInvitation:

    @pytest.mark.asyncio
    async def test_cancel_invitation_success(self):
        svc = make_service()
        owner = make_user()
        invitation = make_request(request_type=RequestType.INVITE)
        company = make_company(company_id=invitation.company_id, owner_id=owner.id)

        svc.repo.get_request_by_id.return_value = invitation
        svc.company_repo.get_company_by_id.return_value = company
        svc.repo.update_request.return_value = invitation

        await svc.cancel_invitation(invitation.id, owner)

        assert invitation.status == RequestStatus.CANCELED

    @pytest.mark.asyncio
    async def test_cancel_invitation_forbidden_not_owner(self):
        svc = make_service()
        invitation = make_request(request_type=RequestType.INVITE)
        company = make_company(company_id=invitation.company_id, owner_id=uuid.uuid4())

        svc.repo.get_request_by_id.return_value = invitation
        svc.company_repo.get_company_by_id.return_value = company

        with pytest.raises(HTTPException) as exc:
            await svc.cancel_invitation(invitation.id, make_user())  # не owner

        assert exc.value.status_code == 403


# ============================================================
# accept_join_request (Owner)
# ============================================================

class TestAcceptJoinRequest:

    @pytest.mark.asyncio
    async def test_accept_join_request_success(self):
        svc = make_service()
        owner = make_user()
        company = make_company(owner_id=owner.id)
        join_request = make_request(
            company_id=company.id,
            user_id=uuid.uuid4(),
            request_type=RequestType.REQUEST,
        )

        svc.repo.get_request_by_id.return_value = join_request
        svc.company_repo.get_company_by_id.return_value = company
        svc.repo.update_request.return_value = join_request
        svc.member_repo.create_membership.return_value = MagicMock()

        await svc.accept_join_request(join_request.id, owner)

        assert join_request.status == RequestStatus.ACCEPTED
        svc.member_repo.create_membership.assert_called_once()


# ============================================================
# decline_join_request (Owner)
# ============================================================

class TestDeclineJoinRequest:

    @pytest.mark.asyncio
    async def test_decline_join_request_success(self):
        svc = make_service()
        owner = make_user()
        join_request = make_request(request_type=RequestType.REQUEST)
        company = make_company(company_id=join_request.company_id, owner_id=owner.id)

        svc.repo.get_request_by_id.return_value = join_request
        svc.company_repo.get_company_by_id.return_value = company
        svc.repo.update_request.return_value = join_request

        await svc.decline_join_request(join_request.id, owner)

        assert join_request.status == RequestStatus.DECLINED


# ============================================================
# get_my_invitations / get_my_join_requests
# ============================================================

class TestGetMyRequests:

    @pytest.mark.asyncio
    async def test_get_my_invitations(self):
        svc = make_service()
        user = make_user()
        invitation = make_request(user_id=user.id, request_type=RequestType.INVITE)
        svc.repo.get_invitations_by_user.return_value = ([invitation], 1)

        result = await svc.get_my_invitations(user, page=1, per_page=10)

        assert result.total == 1

    @pytest.mark.asyncio
    async def test_get_my_join_requests(self):
        svc = make_service()
        user = make_user()
        join_request = make_request(user_id=user.id, request_type=RequestType.REQUEST)
        svc.repo.get_requests_by_user.return_value = ([join_request], 1)

        result = await svc.get_my_join_requests(user, page=1, per_page=10)

        assert result.total == 1


# ============================================================
# get_company_invitations / get_company_join_requests (Owner)
# ============================================================

class TestGetCompanyRequests:

    @pytest.mark.asyncio
    async def test_get_company_invitations_success(self):
        svc = make_service()
        owner = make_user()
        company = make_company(owner_id=owner.id)
        invitation = make_request(company_id=company.id, request_type=RequestType.INVITE)

        svc.company_repo.get_company_by_id.return_value = company
        svc.repo.get_invitations_by_company.return_value = ([invitation], 1)

        result = await svc.get_company_invitations(company.id, owner, page=1, per_page=10)

        assert result.total == 1

    @pytest.mark.asyncio
    async def test_get_company_invitations_forbidden_not_owner(self):
        svc = make_service()
        company = make_company(owner_id=uuid.uuid4())
        svc.company_repo.get_company_by_id.return_value = company

        with pytest.raises(HTTPException) as exc:
            await svc.get_company_invitations(company.id, make_user(), page=1, per_page=10)

        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_company_join_requests_success(self):
        svc = make_service()
        owner = make_user()
        company = make_company(owner_id=owner.id)
        join_request = make_request(company_id=company.id, request_type=RequestType.REQUEST)

        svc.company_repo.get_company_by_id.return_value = company
        svc.repo.get_join_requests_by_company.return_value = ([join_request], 1)

        result = await svc.get_company_join_requests(company.id, owner, page=1, per_page=10)

        assert result.total == 1
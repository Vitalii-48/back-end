# app/services/company_request_service.py

import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company_actions import CompanyMember, CompanyRequest
from app.models.enums import RequestType, RequestStatus, CompanyRole
from app.models.user import User
from app.repositories.company_member_repository import CompanyMemberRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.company_request_repository import CompanyRequestRepository
from app.schemas.company_actions import (
    CompanyRequestResponse,
    CompanyRequestsListResponse,
)

logger = logging.getLogger(__name__)


class CompanyRequestService:
    def __init__(self, session: AsyncSession):
        self.repo = CompanyRequestRepository(session)
        self.member_repo = CompanyMemberRepository(session)
        self.company_repo = CompanyRepository(session)

    # ───────────────────── Створення заявок ─────────────────────

    async def invite_user(
        self, company_id: UUID, invited_user_id: UUID, current_user: User
    ) -> CompanyRequestResponse:
        """
        Owner запрошує користувача.
        Subtask: 'Allow the Owner to send unlimited invitations to other users.'
        """
        company = await self.company_repo.get_company_by_id(company_id)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        if company.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

        await self._ensure_not_already_member(company_id, invited_user_id)
        await self._ensure_no_pending_request(company_id, invited_user_id, RequestType.INVITE)

        invite = CompanyRequest(
            company_id=company_id,
            user_id=invited_user_id,
            type=RequestType.INVITE,
            status=RequestStatus.PENDING,
        )
        created = await self.repo.create_request(invite)
        logger.info(f"Owner {current_user.id} invited user {invited_user_id} to company {company_id}")
        return CompanyRequestResponse.model_validate(created)

    async def request_to_join(self, company_id: UUID, current_user: User) -> CompanyRequestResponse:
        """
        Subtask: 'Users can request to join a company.'
        """
        company = await self.company_repo.get_company_by_id(company_id)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

        await self._ensure_not_already_member(company_id, current_user.id)
        await self._ensure_no_pending_request(company_id, current_user.id, RequestType.REQUEST)

        join_request = CompanyRequest(
            company_id=company_id,
            user_id=current_user.id,
            type=RequestType.REQUEST,
            status=RequestStatus.PENDING,
        )
        created = await self.repo.create_request(join_request)
        logger.info(f"User {current_user.id} requested to join company {company_id}")
        return CompanyRequestResponse.model_validate(created)

    # ───────────────────── Дії над заявками (з боку отримувача) ─────────────────────

    async def accept_invitation(self, request_id: UUID, current_user: User) -> None:
        """Subtask: 'Users can accept an invitation to automatically become members.'"""
        request = await self._get_owned_pending_request(
            request_id, current_user.id, RequestType.INVITE
        )
        await self._convert_request_to_membership(request)
        logger.info(f"User {current_user.id} accepted invitation {request_id}")

    async def decline_invitation(self, request_id: UUID, current_user: User) -> None:
        """Subtask: 'Users can decline an invitation.'"""
        request = await self._get_owned_pending_request(
            request_id, current_user.id, RequestType.INVITE
        )
        request.status = RequestStatus.DECLINED
        await self.repo.update_request(request)
        logger.info(f"User {current_user.id} declined invitation {request_id}")

    async def cancel_join_request(self, request_id: UUID, current_user: User) -> None:
        """Subtask: 'Users... can cancel their own requests.'"""
        request = await self._get_owned_pending_request(
            request_id, current_user.id, RequestType.REQUEST
        )
        request.status = RequestStatus.CANCELED
        await self.repo.update_request(request)
        logger.info(f"User {current_user.id} canceled join request {request_id}")

    # ───────────────────── Дії над заявками (з боку Owner-а) ─────────────────────

    async def cancel_invitation(self, request_id: UUID, current_user: User) -> None:
        """Subtask: 'Enable the Owner to cancel any sent invitations.'"""
        request = await self._get_request_for_owner(request_id, current_user.id, RequestType.INVITE)
        request.status = RequestStatus.CANCELED
        await self.repo.update_request(request)
        logger.info(f"Owner {current_user.id} canceled invitation {request_id}")

    async def accept_join_request(self, request_id: UUID, current_user: User) -> None:
        """Subtask: 'The Owner can accept... membership requests.'"""
        request = await self._get_request_for_owner(request_id, current_user.id, RequestType.REQUEST)
        await self._convert_request_to_membership(request)
        logger.info(f"Owner {current_user.id} accepted join request {request_id}")

    async def decline_join_request(self, request_id: UUID, current_user: User) -> None:
        """Subtask: 'The Owner can... decline membership requests.'"""
        request = await self._get_request_for_owner(request_id, current_user.id, RequestType.REQUEST)
        request.status = RequestStatus.DECLINED
        await self.repo.update_request(request)
        logger.info(f"Owner {current_user.id} declined join request {request_id}")

    # ───────────────────── Списки (read endpoints) ─────────────────────

    async def get_my_invitations(
        self, current_user: User, page: int, per_page: int
    ) -> CompanyRequestsListResponse:
        """Subtask: 'view their list of received invitations.'"""
        skip = (page - 1) * per_page
        items, total = await self.repo.get_invitations_by_user(current_user.id, skip, per_page)
        return CompanyRequestsListResponse(
            requests=[CompanyRequestResponse.model_validate(i) for i in items], total=total
        )

    async def get_my_join_requests(
        self, current_user: User, page: int, per_page: int
    ) -> CompanyRequestsListResponse:
        """Subtask: 'view their list of membership requests.'"""
        skip = (page - 1) * per_page
        items, total = await self.repo.get_requests_by_user(current_user.id, skip, per_page)
        return CompanyRequestsListResponse(
            requests=[CompanyRequestResponse.model_validate(i) for i in items], total=total
        )

    async def get_company_invitations(
        self, company_id: UUID, current_user: User, page: int, per_page: int
    ) -> CompanyRequestsListResponse:
        """Subtask (Owner): 'view the list of invited users.'"""
        await self._ensure_is_owner(company_id, current_user.id)
        skip = (page - 1) * per_page
        items, total = await self.repo.get_invitations_by_company(company_id, skip, per_page)
        return CompanyRequestsListResponse(
            requests=[CompanyRequestResponse.model_validate(i) for i in items], total=total
        )

    async def get_company_join_requests(
        self, company_id: UUID, current_user: User, page: int, per_page: int
    ) -> CompanyRequestsListResponse:
        """Subtask (Owner): 'view the list of pending membership requests.'"""
        await self._ensure_is_owner(company_id, current_user.id)
        skip = (page - 1) * per_page
        items, total = await self.repo.get_join_requests_by_company(company_id, skip, per_page)
        return CompanyRequestsListResponse(
            requests=[CompanyRequestResponse.model_validate(i) for i in items], total=total
        )

    # ───────────────────── Внутрішні (private) допоміжні методи ─────────────────────

    async def _ensure_not_already_member(self, company_id: UUID, user_id: UUID) -> None:
        existing = await self.member_repo.get_membership_by_company_and_user(company_id, user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this company",
            )

    async def _ensure_no_pending_request(
        self, company_id: UUID, user_id: UUID, request_type: RequestType
    ) -> None:
        existing = await self.repo.get_pending_request(company_id, user_id, request_type)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A pending request of this type already exists",
            )

    async def _ensure_is_owner(self, company_id: UUID, user_id: UUID) -> None:
        company = await self.company_repo.get_company_by_id(company_id)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        if company.owner_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    async def _get_owned_pending_request(
        self, request_id: UUID, user_id: UUID, request_type: RequestType
    ) -> CompanyRequest:
        """
        Дістає PENDING заявку та перевіряє, що саме цей user є її адресатом
        (тобто request.user_id == user_id). Використовується, коли діє
        отримувач заявки (приймає/відхиляє інвайт, скасовує власний реквест).
        """
        request = await self.repo.get_request_by_id(request_id)
        if not request or request.type != request_type:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
        if request.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        if request.status != RequestStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request has already been resolved",
            )
        return request

    async def _get_request_for_owner(
        self, request_id: UUID, owner_id: UUID, request_type: RequestType
    ) -> CompanyRequest:
        """
        Дістає PENDING заявку та перевіряє, що current_user є Owner-ом
        компанії, до якої належить ця заявка. Використовується для дій
        Owner-а (cancel invite, accept/decline join request).
        """
        request = await self.repo.get_request_by_id(request_id)
        if not request or request.type != request_type:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

        company = await self.company_repo.get_company_by_id(request.company_id)
        if not company or company.owner_id != owner_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

        if request.status != RequestStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request has already been resolved",
            )
        return request

    async def _convert_request_to_membership(self, request: CompanyRequest) -> CompanyMember:
        """
        Спільна логіка для 'accept_invitation' і 'accept_join_request':
        заявка стає ACCEPTED, і одночасно створюється запис CompanyMember.
        """
        request.status = RequestStatus.ACCEPTED
        await self.repo.update_request(request)

        membership = CompanyMember(
            company_id=request.company_id,
            user_id=request.user_id,
            role=CompanyRole.MEMBER,
        )
        return await self.member_repo.create_membership(membership)
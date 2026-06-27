# app/repositories/company_request_repository.py

import logging
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company_actions import CompanyRequest
from app.models.enums import RequestType, RequestStatus

logger = logging.getLogger(__name__)


class CompanyRequestRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_request(self, request: CompanyRequest) -> CompanyRequest:
        """Створює INVITE (від Owner-а) або REQUEST (від користувача)."""
        self.session.add(request)
        await self.session.commit()
        await self.session.refresh(request)
        return request

    async def update_request(self, request: CompanyRequest) -> CompanyRequest:
        """Оновлює статус заявки (PENDING -> ACCEPTED/DECLINED/CANCELED)."""
        await self.session.commit()
        await self.session.refresh(request)
        return request

    async def delete_request(self, request: CompanyRequest) -> None:
        await self.session.delete(request)
        await self.session.commit()

    async def get_request_by_id(self, request_id: UUID) -> CompanyRequest | None:
        result = await self.session.execute(
            select(CompanyRequest).where(CompanyRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def get_pending_request(
        self, company_id: UUID, user_id: UUID, request_type: RequestType
    ) -> CompanyRequest | None:
        """
        Шукає активну (PENDING) заявку конкретного типу для пари company+user.
        Потрібно перед створенням нової заявки (захист від дублікатів)
        та перед accept/decline/cancel (щоб знайти, що саме змінювати).
        """
        result = await self.session.execute(
            select(CompanyRequest).where(
                CompanyRequest.company_id == company_id,
                CompanyRequest.user_id == user_id,
                CompanyRequest.type == request_type,
                CompanyRequest.status == RequestStatus.PENDING,
            )
        )
        return result.scalar_one_or_none()

    async def get_invitations_by_user(
        self, user_id: UUID, skip: int = 0, limit: int = 10
    ) -> tuple[list[CompanyRequest], int]:
        """Список вхідних запрошень користувача (subtask: 'view list of received invitations')."""
        query = select(CompanyRequest).where(
            CompanyRequest.user_id == user_id,
            CompanyRequest.type == RequestType.INVITE,
            CompanyRequest.status == RequestStatus.PENDING,
        )
        result = await self.session.execute(query.offset(skip).limit(limit))
        invitations = list(result.scalars().all())

        total = await self.session.scalar(
            select(func.count(CompanyRequest.id)).where(
                CompanyRequest.user_id == user_id,
                CompanyRequest.type == RequestType.INVITE,
                CompanyRequest.status == RequestStatus.PENDING,
            )
        )
        return invitations, total or 0

    async def get_requests_by_user(
        self, user_id: UUID, skip: int = 0, limit: int = 10
    ) -> tuple[list[CompanyRequest], int]:
        """Список запитів на вступ, які подав сам користувач (subtask: 'view list of membership requests')."""
        query = select(CompanyRequest).where(
            CompanyRequest.user_id == user_id,
            CompanyRequest.type == RequestType.REQUEST,
            CompanyRequest.status == RequestStatus.PENDING,
        )
        result = await self.session.execute(query.offset(skip).limit(limit))
        requests = list(result.scalars().all())

        total = await self.session.scalar(
            select(func.count(CompanyRequest.id)).where(
                CompanyRequest.user_id == user_id,
                CompanyRequest.type == RequestType.REQUEST,
                CompanyRequest.status == RequestStatus.PENDING,
            )
        )
        return requests, total or 0

    async def get_invitations_by_company(
        self, company_id: UUID, skip: int = 0, limit: int = 10
    ) -> tuple[list[CompanyRequest], int]:
        """Список запрошених юзерів для Owner-а (subtask: 'view list of invited users')."""
        query = select(CompanyRequest).where(
            CompanyRequest.company_id == company_id,
            CompanyRequest.type == RequestType.INVITE,
            CompanyRequest.status == RequestStatus.PENDING,
        )
        result = await self.session.execute(query.offset(skip).limit(limit))
        invitations = list(result.scalars().all())

        total = await self.session.scalar(
            select(func.count(CompanyRequest.id)).where(
                CompanyRequest.company_id == company_id,
                CompanyRequest.type == RequestType.INVITE,
                CompanyRequest.status == RequestStatus.PENDING,
            )
        )
        return invitations, total or 0

    async def get_join_requests_by_company(
        self, company_id: UUID, skip: int = 0, limit: int = 10
    ) -> tuple[list[CompanyRequest], int]:
        """Список запитів на вступ для Owner-а (subtask: 'view list of pending membership requests')."""
        query = select(CompanyRequest).where(
            CompanyRequest.company_id == company_id,
            CompanyRequest.type == RequestType.REQUEST,
            CompanyRequest.status == RequestStatus.PENDING,
        )
        result = await self.session.execute(query.offset(skip).limit(limit))
        requests = list(result.scalars().all())

        total = await self.session.scalar(
            select(func.count(CompanyRequest.id)).where(
                CompanyRequest.company_id == company_id,
                CompanyRequest.type == RequestType.REQUEST,
                CompanyRequest.status == RequestStatus.PENDING,
            )
        )
        return requests, total or 0
# app/repositories/company_member_repository.py

import logging
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company_actions import CompanyMember

logger = logging.getLogger(__name__)


class CompanyMemberRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create_membership(self, membership: CompanyMember) -> CompanyMember:
        """Додає новий запис членства (наприклад, коли заявку прийнято)."""
        self.db_session.add(membership)
        await self.db_session.commit()
        await self.db_session.refresh(membership)
        return membership

    async def delete_membership(self, membership: CompanyMember) -> None:
        """Видаляє членство (Owner видалив юзера, або юзер сам вийшов)."""
        await self.db_session.delete(membership)
        await self.db_session.commit()

    async def get_membership_by_id(self, membership_id: UUID) -> CompanyMember | None:
        result = await self.db_session.execute(
            select(CompanyMember).where(CompanyMember.id == membership_id)
        )
        return result.scalar_one_or_none()

    async def get_membership_by_company_and_user(
        self, company_id: UUID, user_id: UUID
    ) -> CompanyMember | None:
        """
        Перевірити, чи user вже є членом company.
        Використовується перед прийняттям заявки та перед перевіркою прав доступу.
        """
        result = await self.db_session.execute(
            select(CompanyMember).where(
                CompanyMember.company_id == company_id,
                CompanyMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_members_by_company(
        self, company_id: UUID, skip: int = 0, limit: int = 10
    ) -> tuple[list[CompanyMember], int]:
        """Список членів компанії з пагінацією (subtask: 'view the list of users in a company')."""
        result = await self.db_session.execute(
            select(CompanyMember)
            .where(CompanyMember.company_id == company_id)
            .offset(skip)
            .limit(limit)
        )
        members = list(result.scalars().all())

        total = await self.db_session.scalar(
            select(func.count(CompanyMember.id)).where(
                CompanyMember.company_id == company_id
            )
        )
        logger.debug(
            f"Fetched {len(members)} members for company={company_id}, total={total}"
        )
        return members, total or 0
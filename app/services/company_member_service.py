# app/services/company_member_service.py

import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company_actions import CompanyMember
from app.models.enums import CompanyRole
from app.models.user import User
from app.repositories.company_member_repository import CompanyMemberRepository
from app.repositories.company_repository import CompanyRepository
from app.schemas.company_actions import CompanyMembersListResponse, CompanyMemberResponse, CompanyAdminsListResponse

logger = logging.getLogger(__name__)


class CompanyMemberService:
    def __init__(self, session: AsyncSession):
        self.member_repo = CompanyMemberRepository(session)
        self.company_repo = CompanyRepository(session)

    async def create_owner_membership(self, company_id: UUID, user_id: UUID) -> CompanyMember:
        """
        Викликається одразу при створенні компанії:
        Owner автоматично стає CompanyMember з роллю OWNER.
        """
        membership = CompanyMember(
            company_id=company_id,
            user_id=user_id,
            role=CompanyRole.OWNER,
        )
        return await self.member_repo.create_membership(membership)

    async def get_members(
        self, company_id: UUID, page: int, per_page: int
    ) -> CompanyMembersListResponse:
        """Endpoint: 'view the list of users in a company' (з пагінацією)."""
        skip = (page - 1) * per_page
        members, total = await self.member_repo.get_members_by_company(
            company_id, offset=skip, limit=per_page
        )
        return CompanyMembersListResponse(
            members=[CompanyMemberResponse.model_validate(m) for m in members],
            total=total,
        )

    async def remove_member(self, company_id: UUID, member_user_id: UUID, current_user: User) -> None:
        """
        Owner видаляє користувача з компанії.
        """
        company = await self.company_repo.get_company_by_id(company_id)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        if company.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

        # Owner не може видалити сам себе через цей метод - для цього є інша дія
        if member_user_id == company.owner_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Owner cannot be removed from their own company",
            )

        membership = await self.member_repo.get_membership_by_company_and_user(company_id, member_user_id)
        if not membership:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")

        await self.member_repo.delete_membership(membership)
        logger.info(f"Owner {current_user.id} removed user {member_user_id} from company {company_id}")

    async def leave_company(self, company_id: UUID, current_user: User) -> None:
        """
        Subtask: 'Enable users to leave the company on their own.'
        """
        company = await self.company_repo.get_company_by_id(company_id)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

        # Owner не може просто "вийти" - спочатку треба передати компанію
        # або видалити її; інакше компанія залишиться без власника.
        if company.owner_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Owner cannot leave their own company, delete it instead",
            )

        membership = await self.member_repo.get_membership_by_company_and_user(company_id, current_user.id)
        if not membership:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")

        await self.member_repo.delete_membership(membership)
        logger.info(f"User {current_user.id} left company {company_id}")


    async def change_role(
            self,
            company_id: UUID,
            user_id: UUID,
            new_role: CompanyRole,
            current_user: User,
    ) -> CompanyMember:
        """
        Централізований метод зміни ролі учасника.
        Доступно тільки для Owner. Використовується для призначення/зняття адміна.
        """
        # 1. Перевірка існування компанії
        company = await self.company_repo.get_company_by_id(company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )

        # 2. Перевірка прав — тільки Owner може змінювати ролі
        requester = await self.member_repo.get_membership_by_company_and_user(
            company_id, current_user.id
        )
        if not requester or requester.role != CompanyRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only company owners can manage administrators"
            )

        # 3. Перевірка що цільовий юзер є учасником компанії
        target_member = await self.member_repo.get_membership_by_company_and_user(
            company_id, user_id
        )
        if not target_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User is not a member of this company"
            )

        # 4. Заборона змінювати роль Owner-а
        if target_member.role == CompanyRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change owner role"
            )

        # 5. Заборона встановлювати ту саму роль що вже є
        if target_member.role == new_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User already has role {new_role.value}"
            )

        return await self.member_repo.update_member_role(target_member, new_role)


    async def get_admins(
            self,
            company_id: UUID,
            current_user: User,
            offset: int = 0,
            limit: int = 10,
    ) -> CompanyAdminsListResponse:
        """
        Отримання списку адміністраторів компанії.
        """
        # 1. Перевірка існування компанії
        company = await self.company_repo.get_company_by_id(company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )
        # 2. Запитувач є членом компанії?
        requester = await self.member_repo.get_membership_by_company_and_user(
            company_id, current_user.id
        )
        if not requester:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this company"
            )

        # Розпаковуємо (unpack) tuple у дві окремі змінні
        admins, total = await self.member_repo.get_admins_by_company_id(
            company_id, offset, limit
        )
        # 3. Прямий виклик оптимізованого SQL-запиту з репозиторію
        return CompanyAdminsListResponse(
            admins=[CompanyMemberResponse.model_validate(a) for a in admins],
            total=total,
        )
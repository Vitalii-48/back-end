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
            company_id, skip=skip, limit=per_page
        )
        return CompanyMembersListResponse(
            members=[CompanyMemberResponse.model_validate(m) for m in members],
            total=total,
        )

    async def remove_member(self, company_id: UUID, member_user_id: UUID, current_user: User) -> None:
        """
        Owner видаляє користувача з компанії.
        Subtask: 'Allow the Owner to remove users from the company.'
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

    async def make_admin(self, company_id: UUID, user_id: UUID, current_user: User):
        """
        Бізнес-логіка призначення користувача адміністратором компанії.
        Доступно тільки для Owner.
        """
        # 1. Перевірка існування компанії (Тест: test_make_admin_company_not_found)
        company = await self.company_repo.get_company_by_id(company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )

        # 2. Перевірка прав ініціатора (Тест: test_make_admin_forbidden_for_non_owner)
        requester = await self.member_repo.get_membership_by_company_and_user(company_id, current_user.id)
        if not requester or requester.role != CompanyRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only company owners can manage administrators"
            )

        # 3. Перевірка, чи цільовий користувач взагалі є в компанії (Тест: test_make_admin_target_not_member)
        target_member = await self.member_repo.get_membership_by_company_and_user(company_id, user_id)
        if not target_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User is not a member of this company"
            )

        # 4. Заборона змінювати роль Owner-а (Тест: test_make_admin_cannot_change_owner_role)
        if target_member.role == CompanyRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change owner role"
            )

        # 5. Заборона повторного призначення (Тест: test_make_admin_already_admin)
        if target_member.role == CompanyRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already an administrator"
            )

        # 6. Виклик "тупого" мутуючого методу репозиторію
        return await self.member_repo.update_member_role(target_member, CompanyRole.ADMIN)

    async def remove_admin(self, company_id: UUID, user_id: UUID, current_user: User):
        """
        Бізнес-логіка зняття адмінських прав з користувача (пониження до MEMBER).
        Доступно тільки для Owner.
        """
        # 1. Перевірка існування компанії
        company = await self.company_repo.get_company_by_id(company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )

        # 2. Перевірка прав ініціатора (має бути OWNER)
        requester = await self.member_repo.get_membership_by_company_and_user(company_id, current_user.id)
        if not requester or requester.role != CompanyRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only company owners can manage administrators"
            )

        # 3. Перевірка існування цільового членства
        target_member = await self.member_repo.get_membership_by_company_and_user(company_id, user_id)
        if not target_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User is not a member of this company"
            )

        # 4. Перевірка, чи користувач дійсно є адміном (Тест: test_remove_admin_user_not_admin)
        if target_member.role != CompanyRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not an administrator"
            )

        # 5. Зняття ролі до звичайного MEMBER
        return await self.member_repo.update_member_role(target_member, CompanyRole.MEMBER)

    async def get_admins(self, company_id: UUID, offset: int = 0, limit: int = 10):
        """
        Отримання списку адміністраторів компанії.
        (Тести: test_get_admins_returns_list / test_get_admins_company_not_found)
        """
        # 1. Перевірка існування компанії
        company = await self.company_repo.get_company_by_id(company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )

        # Розпаковуємо (unpack) tuple у дві окремі змінні
        admins, total = await self.member_repo.get_admins_by_company_id(
            company_id, offset, limit
        )
        # 2. Прямий виклик оптимізованого SQL-запиту з репозиторію
        return CompanyAdminsListResponse(
            admins=[CompanyMemberResponse.model_validate(a) for a in admins],
            total=total,
        )
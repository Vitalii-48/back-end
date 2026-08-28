# app/services/permissions.py
from uuid import UUID
from fastapi import HTTPException, status

from app.repositories.company_member_repository import CompanyMemberRepository
from app.models.enums import CompanyRole


async def ensure_admin(
    member_repo: CompanyMemberRepository, user_id: UUID, company_id: UUID
) -> None:
    """
    Кидає 403 якщо юзер не є Owner або Admin компанії.
    Спільна перевірка, якою користуються QuizService, QuizImportService
    та будь-який інший сервіс, що потребує такого ж role check —
    щоб не дублювати правило в кількох місцях.
    """
    membership = await member_repo.get_membership_by_company_and_user(
        user_id=user_id, company_id=company_id
    )
    if not membership or membership.role not in (CompanyRole.OWNER, CompanyRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас немає прав для цієї дії.",
        )


async def ensure_member(
    member_repo: CompanyMemberRepository, user_id: UUID, company_id: UUID
) -> None:
    """Кидає 403 якщо user не є учасником компанії."""
    membership = await member_repo.get_membership_by_company_and_user(
        user_id=user_id, company_id=company_id
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this company.",
        )
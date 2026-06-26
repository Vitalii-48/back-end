# app/routers/company_members.py

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import get_current_user, get_company_member_service
from app.models.user import User
from app.models.enums import CompanyRole
from app.schemas.company_actions import (
    CompanyMembersListResponse,
    CompanyAdminsListResponse,
    CompanyMemberResponse)
from app.services.company_member_service import CompanyMemberService

router = APIRouter(prefix="/company", tags=["Company Members"])


@router.get("/{company_id}/members", response_model=CompanyMembersListResponse)
async def get_company_members(
    company_id: UUID,
    page: int = Query(default=1, ge=1, description="Номер сторінки (page number)"),
    per_page: int = Query(default=10, ge=1, le=100, description="Кількість на сторінці"),
    member_service: CompanyMemberService = Depends(get_company_member_service),
):
    """Список учасників компанії (subtask: 'view the list of users in a company')."""
    return await member_service.get_members(company_id, page, per_page)


@router.delete("/{company_id}/members/me", status_code=status.HTTP_204_NO_CONTENT)
async def leave_company(
    company_id: UUID,
    current_user: User = Depends(get_current_user),
    member_service: CompanyMemberService = Depends(get_company_member_service),
):
    """Користувач самостійно виходить з компанії."""
    await member_service.leave_company(company_id, current_user)


@router.delete("/{company_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_company_member(
    company_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    member_service: CompanyMemberService = Depends(get_company_member_service),
):
    """Owner видаляє користувача з компанії."""
    await member_service.remove_member(company_id, user_id, current_user)


@router.post(
    "/{company_id}/admins/{user_id}",
    response_model=CompanyMemberResponse,
)
async def make_admin(
        company_id: UUID,
        user_id: UUID,
        current_user: User = Depends(get_current_user),
        member_service: CompanyMemberService = Depends(get_company_member_service),
):
    """
    Owner призначає учасника компанії адміністратором.
    """
    return await member_service.change_role(
        company_id, user_id, CompanyRole.ADMIN, current_user)

@router.delete(
    "/{company_id}/admins/{user_id}",
    response_model=CompanyMemberResponse,
)
async def remove_admin(
        company_id: UUID,
        user_id: UUID,
        current_user: User = Depends(get_current_user),
        member_service: CompanyMemberService = Depends(get_company_member_service),):
    """
    Owner знімає роль адміністратора з учасника, повертаючи його до MEMBER.
    """
    return await member_service.remove_admin(company_id, user_id, CompanyRole.MEMBER, current_user)

@router.get(
    "/{company_id}/admins",
    response_model=CompanyAdminsListResponse,
)
async def get_admins(
        company_id: UUID,
        page: int = Query(default=1, ge=1, description="Номер сторінки"),
        per_page: int = Query(default=10, ge=1, le=100, description="Кількість на сторінці"),
        current_user: User = Depends(get_current_user),
        member_service: CompanyMemberService = Depends(get_company_member_service),
):
    """
    Повертає список адміністраторів компанії з пагінацією.
    """
    return await member_service.get_admins(company_id, page, per_page)


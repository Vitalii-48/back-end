# app/routers/company_requests.py

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import get_current_user, get_company_request_service
from app.models.user import User
from app.schemas.company_actions import (
    CompanyInviteCreateRequest,
    CompanyRequestResponse,
    CompanyRequestsListResponse,
)
from app.services.company_request_service import CompanyRequestService

router = APIRouter(prefix="/company", tags=["Company Requests"])


# ───────────────────── Створення заявок ─────────────────────

@router.post(
    "/{company_id}/invitations",
    response_model=CompanyRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invite_user_to_company(
    company_id: UUID,
    data: CompanyInviteCreateRequest,
    current_user: User = Depends(get_current_user),
    request_service: CompanyRequestService = Depends(get_company_request_service),
):
    """Owner надсилає запрошення конкретному користувачу."""
    return await request_service.invite_user(company_id, data.user_id, current_user)


@router.post(
    "/{company_id}/join-requests",
    response_model=CompanyRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_to_join_company(
    company_id: UUID,
    current_user: User = Depends(get_current_user),
    request_service: CompanyRequestService = Depends(get_company_request_service),
):
    """Користувач сам подає запит на вступ до компанії."""
    return await request_service.request_to_join(company_id, current_user)


# ───────────────────── Дії отримувача заявки (поточний юзер) ─────────────────────

@router.post("/invitations/{request_id}/accept", status_code=status.HTTP_204_NO_CONTENT)
async def accept_invitation(
    request_id: UUID,
    current_user: User = Depends(get_current_user),
    request_service: CompanyRequestService = Depends(get_company_request_service),
):
    """Користувач приймає запрошення -> стає членом компанії."""
    await request_service.accept_invitation(request_id, current_user)


@router.post("/invitations/{request_id}/decline", status_code=status.HTTP_204_NO_CONTENT)
async def decline_invitation(
    request_id: UUID,
    current_user: User = Depends(get_current_user),
    request_service: CompanyRequestService = Depends(get_company_request_service),
):
    """Користувач відхиляє запрошення."""
    await request_service.decline_invitation(request_id, current_user)


@router.post("/join-requests/{request_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_own_join_request(
    request_id: UUID,
    current_user: User = Depends(get_current_user),
    request_service: CompanyRequestService = Depends(get_company_request_service),
):
    """Користувач скасовує власний запит на вступ."""
    await request_service.cancel_join_request(request_id, current_user)


# ───────────────────── Дії Owner-а ─────────────────────

@router.post("/invitations/{request_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_invitation(
    request_id: UUID,
    current_user: User = Depends(get_current_user),
    request_service: CompanyRequestService = Depends(get_company_request_service),
):
    """Owner скасовує надіслане ним запрошення."""
    await request_service.cancel_invitation(request_id, current_user)


@router.post("/join-requests/{request_id}/accept", status_code=status.HTTP_204_NO_CONTENT)
async def accept_join_request(
    request_id: UUID,
    current_user: User = Depends(get_current_user),
    request_service: CompanyRequestService = Depends(get_company_request_service),
):
    """Owner приймає запит користувача на вступ -> юзер стає членом."""
    await request_service.accept_join_request(request_id, current_user)


@router.post("/join-requests/{request_id}/decline", status_code=status.HTTP_204_NO_CONTENT)
async def decline_join_request(
    request_id: UUID,
    current_user: User = Depends(get_current_user),
    request_service: CompanyRequestService = Depends(get_company_request_service),
):
    """Owner відхиляє запит користувача на вступ."""
    await request_service.decline_join_request(request_id, current_user)


# ───────────────────── Списки для поточного юзера ─────────────────────

@router.get("/me/invitations", response_model=CompanyRequestsListResponse)
async def get_my_invitations(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    request_service: CompanyRequestService = Depends(get_company_request_service),
):
    """Список запрошень, отриманих поточним користувачем."""
    return await request_service.get_my_invitations(current_user, page, per_page)


@router.get("/me/join-requests", response_model=CompanyRequestsListResponse)
async def get_my_join_requests(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    request_service: CompanyRequestService = Depends(get_company_request_service),
):
    """Список запитів на вступ, поданих поточним користувачем."""
    return await request_service.get_my_join_requests(current_user, page, per_page)


# ───────────────────── Списки для Owner-а ─────────────────────

@router.get("/{company_id}/invitations", response_model=CompanyRequestsListResponse)
async def get_company_invitations(
    company_id: UUID,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    request_service: CompanyRequestService = Depends(get_company_request_service),
):
    """Owner бачить список усіх надісланих запрошень своєї компанії."""
    return await request_service.get_company_invitations(company_id, current_user, page, per_page)


@router.get("/{company_id}/join-requests", response_model=CompanyRequestsListResponse)
async def get_company_join_requests(
    company_id: UUID,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    request_service: CompanyRequestService = Depends(get_company_request_service),
):
    """Owner бачить список усіх запитів на вступ до своєї компанії."""
    return await request_service.get_company_join_requests(company_id, current_user, page, per_page)
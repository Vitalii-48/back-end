# app/routers/analytics_router.py

from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.dependencies import  get_current_user
from app.core.dependencies import get_analytics_service
from app.models.user import User
from app.schemas.analytics import (
    LastAttemptItem,
    MemberLastAttemptItem,
    MemberWeeklyAveragesResponse,
    QuizAveragesResponse,
    UserRatingResponse,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/me/rating", response_model=UserRatingResponse)
async def get_my_rating(
    current_user: User = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
):
    """Загальний рейтинг поточного користувача по всіх компаніях."""
    return await service.get_user_rating(current_user.id)


@router.get("/me/quizzes/{quiz_id}", response_model=QuizAveragesResponse)
async def get_my_quiz_averages(
    quiz_id: UUID,
    current_user: User = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
):
    """Середні бали поточного користувача по одному конкретному квізу, по тижнях."""
    return await service.get_user_quiz_averages(current_user.id, quiz_id)


@router.get("/me/last-attempts", response_model=list[LastAttemptItem])
async def get_my_last_attempts(
    current_user: User = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
):
    """Список квізів поточного користувача з датою останнього проходження."""
    return await service.get_user_last_attempts(current_user.id)

# ---------- Для owner/admin компанії ----------

@router.get(
    "/companies/{company_id}/members",
    response_model=list[MemberWeeklyAveragesResponse],
)
async def get_company_members_averages(
    company_id: UUID,
    current_user: User = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
):
    """Для owner/admin: середні бали всіх учасників компанії, по тижнях."""
    return await service.get_company_members_averages(company_id, current_user)


@router.get(
    "/companies/{company_id}/members/{user_id}",
    response_model=list[QuizAveragesResponse],
)
async def get_company_member_quiz_averages(
    company_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
):
    """Для owner/admin: детальна статистика одного учасника по кожному квізу, по тижнях."""
    return await service.get_member_quiz_averages(company_id, user_id, current_user)


@router.get(
    "/companies/{company_id}/last-attempts",
    response_model=list[MemberLastAttemptItem],
)
async def get_company_last_attempts(
    company_id: UUID,
    current_user: User = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
):
    """Для owner/admin: список усіх учасників компанії з датою їх останньої спроби."""
    return await service.get_company_last_attempts(company_id, current_user)
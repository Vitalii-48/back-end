# app/services/analytics_service.py
from collections import defaultdict
from uuid import UUID

from fastapi import HTTPException, status

from app.models.company import Company
from app.models.enums import CompanyRole
from app.models.user import User
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.quiz_repository import QuizRepository
from app.schemas.analytics import (
    LastAttemptItem,
    MemberLastAttemptItem,
    MemberWeeklyAveragesResponse,
    QuizAveragesResponse,
    UserRatingResponse,
    WeeklyScoreItem,
)


def _safe_percentage(correct: int, total: int) -> float:
    """Ділення з захистом від нуля (division by zero)."""
    if total == 0:
        return 0.0
    return round(correct / total * 100, 2)


class AnalyticsService:
    def __init__(
            self,
            analytics_repository: AnalyticsRepository,
            company_repository: CompanyRepository,
            quiz_repository: QuizRepository,
    ):
        self.analytics_repository = analytics_repository
        self.company_repository = company_repository
        self.quiz_repository = quiz_repository

    @staticmethod
    def _ensure_owner_or_admin(company: Company, current_user: User) -> None:
        """
        Перевіряє права. Працює за правилом "404 перед 403".
        Примітка: company.members має бути завантажено через joinedload в репозиторії.
        """
        is_owner = company.owner_id == current_user.id
        is_admin = any(
            member.user_id == current_user.id and member.role == CompanyRole.ADMIN
            for member in company.members
        )
        if not (is_owner or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owner or admin can view this data",
            )

    # ---------- Для звичайного користувача ----------

    async def get_user_rating(self, user_id: UUID) -> UserRatingResponse:
        row = await self.analytics_repository.get_user_overall_totals(user_id)
        if not row:
            return UserRatingResponse(overall_average=0.0)

        total_correct = row.total_correct or 0
        total_questions = row.total_questions or 0
        return UserRatingResponse(
            overall_average=_safe_percentage(total_correct, total_questions)
        )

    async def get_user_quiz_averages(
            self, user_id: UUID, quiz_id: UUID
    ) -> QuizAveragesResponse:
        quiz = await self.quiz_repository.get_quiz_by_id(quiz_id)
        if quiz is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")

        rows = await self.analytics_repository.get_user_quiz_weekly_totals(
            user_id, quiz_id
        )
        weekly_scores = [
            WeeklyScoreItem(
                week_start=row.week_start.date(),
                average_score=_safe_percentage(row.total_correct, row.total_questions),
            )
            for row in rows
        ]
        return QuizAveragesResponse(
            quiz_id=quiz_id, quiz_title=quiz.title, weekly_scores=weekly_scores
        )

    async def get_user_last_attempts(self, user_id: UUID) -> list[LastAttemptItem]:
        rows = await self.analytics_repository.get_user_last_attempts(user_id)
        if not rows:
            return []

        # ОПТИМІЗАЦІЯ N+1: Збираємо унікальні quiz_id та робимо ОДИН запит до БД
        unique_quiz_ids = list({row.quiz_id for row in rows if row.quiz_id})

        # Припускаємо, що у твоєму QuizRepository є метод пошуку списком, або скористайся глобальним фільтром:
        quizzes = await self.quiz_repository.get_by_ids(unique_quiz_ids)
        quiz_map = {quiz.id: quiz.title for quiz in quizzes}

        result = []
        for row in rows:
            result.append(
                LastAttemptItem(
                    quiz_id=row.quiz_id,
                    quiz_title=quiz_map.get(row.quiz_id, "Unknown"),
                    last_completed_at=row.last_completed_at.date() if row.last_completed_at else None,
                )
            )
        return result

    # ---------- Для owner/admin компанії ----------

    async def get_company_members_averages(
            self, company_id: UUID, current_user: User
    ) -> list[MemberWeeklyAveragesResponse]:
        company = await self.company_repository.get_company_with_members(company_id)
        if company is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

        self._ensure_owner_or_admin(company, current_user)

        rows = await self.analytics_repository.get_company_members_weekly_totals(
            company_id
        )

        grouped: dict[UUID, list[WeeklyScoreItem]] = defaultdict(list)
        for row in rows:
            grouped[row.user_id].append(
                WeeklyScoreItem(
                    week_start=row.week_start.date(),
                    average_score=_safe_percentage(row.total_correct, row.total_questions),
                )
            )

        return [
            MemberWeeklyAveragesResponse(user_id=user_id, weekly_scores=scores)
            for user_id, scores in grouped.items()
        ]

    async def get_member_quiz_averages(
            self, company_id: UUID, user_id: UUID, current_user: User
    ) -> list[QuizAveragesResponse]:
        company = await self.company_repository.get_company_with_members(company_id)
        if company is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

        self._ensure_owner_or_admin(company, current_user)

        rows = await self.analytics_repository.get_member_quiz_weekly_totals(
            company_id, user_id
        )
        if not rows:
            return []

        # ОПТИМІЗАЦІЯ N+1: Знову збираємо унікальні ID квізів замість циклу запитів
        unique_quiz_ids = list({row.quiz_id for row in rows if row.quiz_id})
        quizzes = await self.quiz_repository.get_by_ids(unique_quiz_ids)
        quiz_map = {quiz.id: quiz.title for quiz in quizzes}

        grouped: dict[UUID, list[WeeklyScoreItem]] = defaultdict(list)
        for row in rows:
            grouped[row.quiz_id].append(
                WeeklyScoreItem(
                    week_start=row.week_start.date(),
                    average_score=_safe_percentage(row.total_correct, row.total_questions),
                )
            )

        result = []
        for quiz_id, weekly_scores in grouped.items():
            result.append(
                QuizAveragesResponse(
                    quiz_id=quiz_id,
                    quiz_title=quiz_map.get(quiz_id, "Unknown"),
                    weekly_scores=weekly_scores,
                )
            )
        return result

    async def get_company_last_attempts(
            self, company_id: UUID, current_user: User
    ) -> list[MemberLastAttemptItem]:
        company = await self.company_repository.get_company_with_members(company_id)
        if company is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

        self._ensure_owner_or_admin(company, current_user)

        rows = await self.analytics_repository.get_company_last_attempts(company_id)
        return [
            MemberLastAttemptItem(
                user_id=row.user_id,
                last_completed_at=row.last_completed_at.date() if row.last_completed_at else None,
            )
            for row in rows
        ]
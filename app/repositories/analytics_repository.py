# app/repositories/analytics_repository.py
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quiz_result import QuizResult


class AnalyticsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_overall_totals(self, user_id: UUID) -> Row | None:
        """
        Повертає суму правильних відповідей і суму всіх питань
        по ВСІХ компаніях для одного користувача.
        Використовує func.coalesce, щоб замість None повертати 0.
        """
        stmt = select(
            func.coalesce(func.sum(QuizResult.correct_answers_count), 0).label("total_correct"),
            func.coalesce(func.sum(QuizResult.total_questions_count), 0).label("total_questions"),
        ).where(QuizResult.user_id == user_id)

        result = await self.session.execute(stmt)
        return result.one_or_none()

    async def get_user_quiz_weekly_totals(
        self, user_id: UUID, quiz_id: UUID
    ) -> list[Row]:
        """
        Суми правильних/всіх відповідей по тижнях, для одного
        конкретного квізу одного користувача.
        """
        week_expr = func.date_trunc("week", QuizResult.completed_at)
        stmt = (
            select(
                week_expr.label("week_start"),
                func.sum(QuizResult.correct_answers_count).label("total_correct"),
                func.sum(QuizResult.total_questions_count).label("total_questions"),
            )
            .where(QuizResult.user_id == user_id, QuizResult.quiz_id == quiz_id)
            .group_by(week_expr)
            .order_by(week_expr)
        )
        result = await self.session.execute(stmt)
        return list(result.all())

    async def get_user_last_attempts(self, user_id: UUID) -> list[Row]:
        """
        Для кожного квізу, який проходив користувач — остання дата
        проходження (MAX(completed_at)).
        """
        stmt = (
            select(
                QuizResult.quiz_id,
                func.max(QuizResult.completed_at).label("last_completed_at"),
            )
            .where(QuizResult.user_id == user_id)
            .group_by(QuizResult.quiz_id)
        )
        result = await self.session.execute(stmt)
        return list(result.all())

    async def get_company_members_weekly_totals(
        self, company_id: UUID
    ) -> list[Row]:
        """
        Суми правильних/всіх відповідей по тижнях, окремо для
        кожного учасника компанії.
        """
        week_expr = func.date_trunc("week", QuizResult.completed_at)
        stmt = (
            select(
                QuizResult.user_id,
                week_expr.label("week_start"),
                func.sum(QuizResult.correct_answers_count).label("total_correct"),
                func.sum(QuizResult.total_questions_count).label("total_questions"),
            )
            .where(QuizResult.company_id == company_id)
            .group_by(QuizResult.user_id, week_expr)
            .order_by(QuizResult.user_id, week_expr)
        )
        result = await self.session.execute(stmt)
        return list(result.all())

    async def get_member_quiz_weekly_totals(
        self, company_id: UUID, user_id: UUID
    ) -> list[Row]:
        """
        Те саме, що вище, але для ОДНОГО конкретного учасника,
        з розбивкою по квізах і тижнях одночасно.
        """
        week_expr = func.date_trunc("week", QuizResult.completed_at)
        stmt = (
            select(
                QuizResult.quiz_id,
                week_expr.label("week_start"),
                func.sum(QuizResult.correct_answers_count).label("total_correct"),
                func.sum(QuizResult.total_questions_count).label("total_questions"),
            )
            .where(
                QuizResult.company_id == company_id,
                QuizResult.user_id == user_id,
            )
            .group_by(QuizResult.quiz_id, week_expr)
            .order_by(QuizResult.quiz_id, week_expr)
        )
        result = await self.session.execute(stmt)
        return list(result.all())

    async def get_company_last_attempts(self, company_id: UUID) -> list[Row]:
        """
        Для кожного учасника компанії — дата його останньої спроби
        (будь-якого квізу в цій компанії).
        """
        stmt = (
            select(
                QuizResult.user_id,
                func.max(QuizResult.completed_at).label("last_completed_at"),
            )
            .where(QuizResult.company_id == company_id)
            .group_by(QuizResult.user_id)
        )
        result = await self.session.execute(stmt)
        return list(result.all())
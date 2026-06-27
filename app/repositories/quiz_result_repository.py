# app/repositories/quiz_result_repository.py
from uuid import UUID

from sqlalchemy import select, func, cast, Float
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quiz_result import QuizResult
from app.models.quiz import Quiz


class QuizResultRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_result(
        self,
        user_id: UUID,
        company_id: UUID,
        quiz_id: UUID,
        total_questions: int,
        correct_answers: int,
        score: float,
    ) -> QuizResult:
        result = QuizResult(
            user_id=user_id,
            company_id=company_id,
            quiz_id=quiz_id,
            total_questions_count=total_questions,
            correct_answers_count=correct_answers,
            score=score,
        )
        self._session.add(result)
        await self._session.commit()
        await self._session.refresh(result)
        return result

    async def get_average_score(
        self,
        user_id: UUID,
        company_id: UUID | None = None,
    ) -> float:
        # 1. Рахуємо суми
        sum_correct = func.sum(QuizResult.correct_answers_count)
        sum_total = func.sum(QuizResult.total_questions_count)

        # 2. Приводимо чисельник до Float, щоб уникнути цілочисельного ділення,
        # та використовуємо func.coalesce, щоб повернути 0.0, якщо записів немає
        query = select(
            func.coalesce(
                cast(sum_correct, Float) / cast(sum_total, Float),
                0.0
            )
        ).where(QuizResult.user_id == user_id)

        if company_id:
            query = query.where(QuizResult.company_id == company_id)  # noqa

        result = await self._session.execute(query)
        # Повертаємо результат. Якщо хочеш у відсотках (наприклад, 85.5%), просто помнож на 100.0
        return float(result.scalar() or 0.0)

    async def get_by_id_with_questions(self, quiz_id: UUID) -> Quiz | None:
        result = await self._session.execute(
            select(Quiz).where(Quiz.id == quiz_id)
        )
        return result.scalar_one_or_none()


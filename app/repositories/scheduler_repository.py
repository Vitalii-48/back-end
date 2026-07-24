# app/repositories/scheduler_repository.py
import uuid
from datetime import datetime, timedelta, UTC
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CompanyRole
from app.models.company_actions import CompanyMember
from app.models.company import Company
from app.models.quiz import Quiz
from app.models.quiz_result import QuizResult


class SchedulerRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_users_who_missed_quizzes(self) -> list[tuple[uuid.UUID, str, str]]:
        """
        Знаходить усіх користувачів, які не проходили доступні квізи за останні 24 години.
        Повертає список кортежів: (user_id, company_name, quiz_title)
        """
        time_limit = datetime.now(UTC) - timedelta(hours=24)

        # LEFT JOIN: Шукаємо зв'язки Користувач -> Компанія -> Квіз,
        # де відсутній QuizResult за останні 24 години.
        stmt = (
            select(
                CompanyMember.user_id,
                Company.name.label("company_name"),
                Quiz.title.label("quiz_title")
            )
            .join(Quiz, Quiz.company_id == CompanyMember.company_id)
            .join(Company, Company.id == Quiz.company_id)
            .join(
                QuizResult,
                and_(
                    QuizResult.user_id == CompanyMember.user_id,
                    QuizResult.quiz_id == Quiz.id,
                    QuizResult.completed_at >= time_limit
                ),
                isouter=True
            )
            .where(
                and_(
                    QuizResult.id == None,          # Ті, хто не мав спроб за 24 години
                    CompanyMember.role != CompanyRole.OWNER
                )
            )
        )

        result = await self.session.execute(stmt)
        return result.all()
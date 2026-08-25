# app/services/quiz_service.py
from uuid import UUID
from fastapi import HTTPException, status

from app.models import Company
from app.repositories.company_repository import CompanyRepository
from app.repositories.quiz_repository import QuizRepository
from app.repositories.company_member_repository import CompanyMemberRepository
from app.schemas.quiz import QuizCreateRequest, QuizUpdateRequest, QuizzesListResponse, QuizDetailResponse, \
    QuizShortResponse
from app.models.enums import CompanyRole
from app.core.logger import setup_logger
from app.services.notification_service import NotificationService

logger = setup_logger(__name__)


class QuizService:
    def __init__(
            self,
            quiz_repo: QuizRepository,
            member_repo: CompanyMemberRepository,
            company_repo: CompanyRepository,
            notification_service: NotificationService
    ):
        self.quiz_repo = quiz_repo
        self.member_repo = member_repo
        self.company_repo = company_repo
        self.notification_service = notification_service

    # ── Публічні методи (public methods) ──

    async def create_company_quiz(
            self, company_id: UUID, data: QuizCreateRequest, user_id: UUID
    ) -> QuizDetailResponse:
        # 1. Компанія існує? (404). Зберігаємо результат — нижче він знадобиться
        company = await self._get_company_or_404(company_id=company_id)

        # 2. Перевірка прав (403)
        await self._ensure_admin(user_id=user_id, company_id=company_id)

        logger.info(f"Створення квізу '{data.title}' для компанії {company_id}")

        # 3. Створення квізу в базі (вже є)
        quiz = await self.quiz_repo.create_quiz(company_id=company_id, data=data)

        # 4. Швидке отримання ID усіх учасників компанії
        member_ids = await self.member_repo.get_all_member_user_ids(company_id)

        # 5. Масова розсилка сповіщень через сервіс сповіщень
        if member_ids:
            await self.notification_service.notify_company_about_new_quiz(
                member_ids=member_ids,
                company_name=company.name,
                quiz_title=quiz.title
            )

        return QuizDetailResponse.model_validate(quiz)

    async def get_company_quizzes_list(
        self, company_id: UUID, user_id: UUID, page: int, per_page: int
    ) -> QuizzesListResponse:
        await self._get_company_or_404(company_id=company_id)
        await self._ensure_member(user_id=user_id, company_id=company_id)
        skip = (page - 1) * per_page
        quizzes, total = await self.quiz_repo.get_company_quizzes(
            company_id=company_id, skip=skip, limit=per_page
        )
        quizzes = [QuizShortResponse.model_validate(q) for q in quizzes]
        return QuizzesListResponse(quizzes=quizzes, total=total, page=page, per_page=per_page)

    async def update_company_quiz(
        self, quiz_id: UUID, company_id: UUID, data: QuizUpdateRequest, user_id: UUID
    ) -> QuizDetailResponse:
        await self._get_company_or_404(company_id=company_id)
        await self._ensure_admin(user_id=user_id, company_id=company_id)
        quiz = await self._get_quiz_or_404(quiz_id=quiz_id, company_id=company_id)
        logger.info(f"Оновлення квізу {quiz_id} користувачем {user_id}")
        quiz = await self.quiz_repo.update_quiz(quiz=quiz, data=data)
        return QuizDetailResponse.model_validate(quiz)

    async def get_quiz_detail(
            self, quiz_id: UUID, company_id: UUID, user_id: UUID
    ) -> QuizDetailResponse:
        """Повертає деталі квізу з питаннями та варіантами відповідей."""
        await self._get_company_or_404(company_id=company_id)
        await self._ensure_member(user_id=user_id, company_id=company_id)
        quiz = await self._get_quiz_or_404(quiz_id=quiz_id, company_id=company_id)
        return QuizDetailResponse.model_validate(quiz)

    async def delete_company_quiz(
        self, quiz_id: UUID, company_id: UUID, user_id: UUID
    ) -> None:
        await self._get_company_or_404(company_id=company_id)
        await self._ensure_admin(user_id=user_id, company_id=company_id)
        quiz = await self._get_quiz_or_404(quiz_id=quiz_id, company_id=company_id)
        logger.info(f"Видалення квізу {quiz_id} користувачем {user_id}")
        await self.quiz_repo.delete_quiz(quiz)

    # ── Приватні методи (private methods) ──

    async def _get_company_or_404(self, company_id: UUID) -> Company:
        """Кидає 404 якщо компанія не знайдена. Завжди викликається ПЕРЕД перевіркою прав (403)."""
        company = await self.company_repo.get_company_by_id(company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Компанію не знайдено.",
            )
        return company

    async def _ensure_admin(self, user_id: UUID, company_id: UUID) -> None:
        """Кидає 403 якщо юзер не є Owner або Admin компанії"""
        membership = await self.member_repo.get_membership_by_company_and_user(
            user_id=user_id, company_id=company_id
        )
        if not membership or membership.role not in (CompanyRole.OWNER, CompanyRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )

    async def _ensure_member(self, user_id: UUID, company_id: UUID) -> None:
        """Кидає 403 якщо user не є учасником компанії."""
        membership = await self.member_repo.get_membership_by_company_and_user(
            user_id=user_id,
            company_id=company_id,
        )

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this company.",
            )

    async def _get_quiz_or_404(self, quiz_id: UUID, company_id: UUID):
        """Кидає 404 якщо квіз не знайдено або не належить компанії"""
        quiz = await self.quiz_repo.get_quiz_by_id(quiz_id)
        if not quiz or quiz.company_id != company_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The quiz was not found or does not belong to this company.",
            )
        return quiz
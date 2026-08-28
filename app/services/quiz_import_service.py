# app/services/quiz_import_service.py
import asyncio
import uuid
from zipfile import BadZipFile

from fastapi import HTTPException, status
from openpyxl.utils.exceptions import InvalidFileException

from app.repositories.quiz_repository import QuizRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.company_member_repository import CompanyMemberRepository
from app.services.quiz_validator import QuizValidator
from app.services.permissions import ensure_admin
from app.utils.excel_parser import parse_excel_to_quizzes
from app.schemas.quiz_import import ImportReport
from app.core.logger import setup_logger

logger = setup_logger(__name__)


class QuizImportService:
    def __init__(
        self,
        quiz_repo: QuizRepository,
        member_repo: CompanyMemberRepository,
        company_repo: CompanyRepository,
    ):
        self.quiz_repo = quiz_repo
        self.member_repo = member_repo
        self.company_repo = company_repo

    async def import_quizzes(
        self, company_id: uuid.UUID, file_content: bytes, user_id: uuid.UUID
    ) -> ImportReport:
        # 1. Компанія існує? (404 — завжди перед перевіркою прав)
        await self._get_company_or_404(company_id=company_id)

        # 2. Перевірка прав (403)
        await ensure_admin(self.member_repo, user_id, company_id)

        logger.info(f"Імпорт квізів для компанії {company_id} користувачем {user_id}")

        # 3. Парсинг файлу
        try:
            parsed_quizzes, parse_errors = await asyncio.to_thread(
                parse_excel_to_quizzes,
                file_content,
            )
        except (BadZipFile, InvalidFileException) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Файл пошкоджений або не є коректним Excel-файлом (.xlsx)",
            ) from exc
        report = ImportReport(errors=list(parse_errors))

        # 4. Валідація і збереження для кожного квіза
        for quiz_data in parsed_quizzes:
            validation_errors = QuizValidator.validate(quiz_data)
            if validation_errors:
                report.errors.extend(validation_errors)
                continue

            existing = await self.quiz_repo.get_by_title_and_company(
                quiz_data.title, company_id
            )
            if existing:
                await self.quiz_repo.update_with_questions(existing, quiz_data)
                report.updated.append(quiz_data.title)
            else:
                await self.quiz_repo.create_with_questions(company_id, quiz_data)
                report.created.append(quiz_data.title)

        # 5. Один commit в кінці всього імпорту
        await self.quiz_repo.session.commit()

        return report

    # ── Приватні методи  ──

    async def _get_company_or_404(self, company_id: uuid.UUID):
        """Кидає 404 якщо компанія не знайдена. Завжди викликається ПЕРЕД перевіркою прав (403)."""
        company = await self.company_repo.get_company_by_id(company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Компанію не знайдено.",
            )
        return company
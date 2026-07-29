# app/services/quiz_import_service.py
import uuid

from app.repositories.quiz_repository import QuizRepository
from app.repositories.company_member_repository import CompanyMemberRepository
from app.services.quiz_validator import QuizValidator
from app.services.permissions import ensure_admin
from app.utils.excel_parser import parse_excel_to_quizzes
from app.schemas.quiz_import import ImportReport
from app.core.logger import setup_logger

logger = setup_logger(__name__)


class QuizImportService:
    def __init__(self, quiz_repo: QuizRepository, member_repo: CompanyMemberRepository):
        self.quiz_repo = quiz_repo
        self.member_repo = member_repo

    async def import_quizzes(
        self, company_id: uuid.UUID, file_content: bytes, user_id: uuid.UUID
    ) -> ImportReport:
        # 1. Перевірка прав — раніше за все інше
        await ensure_admin(self.member_repo, user_id, company_id)

        logger.info(f"Імпорт квізів для компанії {company_id} користувачем {user_id}")

        # 2. Парсинг файлу
        parsed_quizzes, parse_errors = parse_excel_to_quizzes(file_content)
        report = ImportReport(errors=list(parse_errors))

        # 3. Валідація + 4. Збереження для кожного квіза
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
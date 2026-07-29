# app/repositories/quiz_repository.py
from uuid import UUID
import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.quiz import Quiz, QuizQuestion, QuizAnswerOption
from app.schemas.quiz import QuizCreateRequest, QuizUpdateRequest
from app.schemas.quiz_import import ParsedQuizData

logger = logging.getLogger(__name__)


class QuizRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_quiz(self, company_id: UUID, data: QuizCreateRequest) -> Quiz:
        """
        Атомарно створює квіз, усі його питання та варіанти відповідей.
        Якщо будь-який етап впаде, база даних повністю відкотить транзакцію.
        """
        # 1. Створюємо головну сутність — Квіз
        quiz = Quiz(
            title=data.title,
            description=data.description,
            company_id=company_id,
        )
        self.session.add(quiz)

        # Надсилаємо INSERT для квізу, щоб БД згенерувала для нього quiz.id
        await self.session.flush()

        # 2. Перебираємо питання з Pydantic-схеми
        for question_data in data.questions:
            question = QuizQuestion(
                quiz_id=quiz.id,  # Використовуємо згенерований id квізу
                title=question_data.title
            )
            self.session.add(question)

            # Надсилаємо INSERT для питання, щоб отриматий його question.id
            await self.session.flush()

            # 3. Перебираємо варіанти відповідей для цього питання
            for option_data in question_data.options:
                option = QuizAnswerOption(
                    question_id=question.id,  # Використовуємо згенерований id питання
                    text=option_data.text,
                    is_correct=option_data.is_correct
                )
                self.session.add(option)

        # 4. Коли вся ієрархія додана в сесію, робимо ОДИН фінальний commit
        await self.session.commit()

        # 5. Оновлюємо об'єкт
        result = await self.session.execute(
            select(Quiz)
            .options(
                selectinload(Quiz.questions).selectinload(QuizQuestion.options)
            )
            .where(Quiz.id == quiz.id)
        )
        return result.scalar_one()

    async def update_quiz(self, quiz: Quiz, data: QuizUpdateRequest) -> Quiz:
        """
        Оновити квіз.
        Якщо передані нові questions — повністю замінюємо старі.
        """
        if data.title is not None:
            quiz.title = data.title
        if data.description is not None:
            quiz.description = data.description

        if data.questions is not None:
            # Видаляємо старі питання (cascade видалить і answer_options автоматично)
            quiz.questions.clear()
            await self.session.flush()

            # Додаємо нові питання
            for question_data in data.questions:
                question = QuizQuestion(title=question_data.title, quiz_id=quiz.id)
                self.session.add(question)
                await self.session.flush()

                for option_data in question_data.options:
                    option = QuizAnswerOption(
                        text=option_data.text,
                        is_correct=option_data.is_correct,
                        question_id=question.id,
                    )
                    self.session.add(option)

        await self.session.commit()
        await self.session.refresh(quiz)
        return quiz

    async def get_quiz_by_id(self, quiz_id: UUID) -> Quiz | None:
        """Отримати деталі одного квізу за його ID разом з питаннями (через selectin)"""
        query = select(Quiz).where(Quiz.id == quiz_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_company_quizzes(self, company_id: UUID, skip: int = 0, limit: int = 10) -> tuple[list[Quiz], int]:
        """
        Отримати список квізів компанії (з пагінацією) та їх загальну кількість.
        """
        # Запит на самі квізи
        query = select(Quiz).where(Quiz.company_id == company_id).offset(skip).limit(limit)
        result = await self.session.execute(query)
        quizzes = list(result.scalars().all())

        # Запит на загальну кількість квізів компанії (для пагінації)
        count_query = select(func.count()).where(Quiz.company_id == company_id)
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        return quizzes, total


    async def delete_quiz(self, quiz: Quiz) -> None:
        """Видалити квіз (cascade видалить питання та відповіді автоматично)"""
        await self.session.delete(quiz)
        await self.session.commit()


    async def increment_frequency(self, quiz_id: UUID) -> None:
        quiz = await self.get_quiz_by_id(quiz_id)
        if quiz:
            quiz.frequency += 1
            await self.session.commit()


    async def get_by_ids(self, quiz_ids: list[UUID]) -> list[Quiz]:
        """Дістає одразу декілька квізів по списку ID (один SQL-запит)."""
        if not quiz_ids:
            return []

        stmt = select(Quiz).where(Quiz.id.in_(quiz_ids))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_title_and_company(
        self, title: str, company_id: UUID
    ) -> Quiz | None:
        """
        lazy="selectin" вже налаштовано у Quiz.questions і
        QuizQuestion.options — SQLAlchemy сам підтягне вкладені
        питання/відповіді без явного selectinload().
        """
        stmt = select(Quiz).where(Quiz.title == title, Quiz.company_id == company_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_with_questions(
        self, company_id: UUID, quiz_data: ParsedQuizData
    ) -> Quiz:
        quiz = Quiz(
            title=quiz_data.title,
            description=quiz_data.description,
            frequency=quiz_data.frequency,
            company_id=company_id,
        )
        for question_data in quiz_data.questions:
            question = QuizQuestion(title=question_data.title)
            for answer_data in question_data.answers:
                question.options.append(
                    QuizAnswerOption(text=answer_data.text, is_correct=answer_data.is_correct)
                )
            quiz.questions.append(question)

        self.session.add(quiz)
        await self.session.flush()
        return quiz

    async def update_with_questions(
        self, quiz: Quiz, quiz_data: ParsedQuizData
    ) -> Quiz:
        """
        ВАЖЛИВО: оновлюємо квіз "на місці" (той самий id!), а не
        видаляємо і створюємо заново — інакше через
        ondelete="CASCADE" на QuizResult.quiz_id стерлась би вся
        історія проходжень цього квіза користувачами.

        cascade="all, delete-orphan" на Quiz.questions і
        QuizQuestion.options означає, що просто очистивши список,
        SQLAlchemy сам згенерує DELETE для старих рядків при flush.
        """
        quiz.title = quiz_data.title
        quiz.description = quiz_data.description
        quiz.frequency = quiz_data.frequency

        quiz.questions.clear()

        for question_data in quiz_data.questions:
            question = QuizQuestion(title=question_data.title)
            for answer_data in question_data.answers:
                question.options.append(
                    QuizAnswerOption(text=answer_data.text, is_correct=answer_data.is_correct)
                )
            quiz.questions.append(question)

        await self.session.flush()
        return quiz
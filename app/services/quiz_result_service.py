from uuid import UUID
from fastapi import HTTPException, status

from app.schemas.quiz_result import QuizSubmitRequest, QuizSubmitResponse
from app.repositories.quiz_cache_repository import QuizCacheRepository

class QuizWorkflowService:
    def __init__(self, quiz_repo, quiz_result_repo, member_repo, user_repo, quiz_cache_repo: QuizCacheRepository):
        self._quiz_repo = quiz_repo
        self._quiz_result_repo = quiz_result_repo
        self._member_repo = member_repo
        self._user_repo = user_repo
        self._quiz_cache_repo = quiz_cache_repo

    async def submit_quiz(
            self,
            company_id: UUID,
            user_id: UUID,
            quiz_id: UUID,
            payload: QuizSubmitRequest,
    ) -> QuizSubmitResponse:

        # 1. Квіз існує? (Переконайся, що метод в репозиторії називається саме так)
        quiz = await self._quiz_repo.get_quiz_by_id(quiz_id)
        if not quiz:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")

        # 2. Квіз належить цій компанії?
        if quiz.company_id != company_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found in this company")

        # 3. Юзер є членом компанії?
        member = await self._member_repo. get_membership_by_company_and_user(company_id=company_id, user_id=user_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this company"
            )

        # 4. Підрахунок правильних відповідей
        user_answers_map = {
            ans.question_id: set(ans.selected_option_ids)
            for ans in payload.answers
        }

        correct_answers = 0
        detailed_answers = []
        for question in quiz.questions:
            correct_ids = {o.id for o in question.options if o.is_correct}
            user_selected = user_answers_map.get(question.id, set())

            is_correct = len(correct_ids) > 0 and not (correct_ids ^ user_selected)

            if is_correct:
                correct_answers += 1

            # Детальна відповідь (detailed answer) по кожному питанню
            detailed_answers.append({
                "question_id": str(question.id),
                "selected_option_ids": [str(oid) for oid in user_selected],
                "is_correct": is_correct,
            })

        total = len(quiz.questions)
        score = round(correct_answers / total, 4) if total > 0 else 0.0

        # 5. Зберегти результат в БД та отримати створений об'єкт моделі
        await self._quiz_result_repo.create_result(
            user_id=user_id,
            company_id=company_id,
            quiz_id=quiz_id,
            total_questions=total,
            correct_answers=correct_answers,
            score=score,
        )

        # 6. Оновити час останньої спроби користувача
        await self._user_repo.update_last_attempt(user_id)

        # 7. Збільшити лічильник проходжень
        await self._quiz_repo.increment_frequency(quiz_id)

        # 8. Зберегти детальні відповіді в Redis на 48 годин  ← додай цей блок
        await self._quiz_cache_repo.save_quiz_attempt(
            user_id=user_id,
            company_id=company_id,
            quiz_id=quiz_id,
            answers=detailed_answers,
        )

        # Автоматично мапимо модель зі всіма ID та score у Pydantic схему
        is_passed = score >= 0.8  # або будь-який твій поріг (наприклад, > 0)
        return QuizSubmitResponse(
            quiz_id=quiz_id,
            correct_answers_count=correct_answers,
            total_questions_count=total,
            is_passed=is_passed,
        )
    async def get_my_average_score(
            self,
            user_id: UUID,
            company_id: UUID | None = None,
    ) -> float:
        return await self._quiz_result_repo.get_average_score(
            user_id=user_id,
            company_id=company_id,
        )

    async def get_user_average_in_company(
            self,
            user_id: UUID,  # Кого перевіряємо
            company_id: UUID,  # В якій компанії
            requesting_user_id: UUID,  # Хто запитує (поточний юзер з токена)
    ) -> float:
        """
        Повертає середній бал користувача в межах конкретної компанії.
        Доступно для owner/admin компанії або самого користувача.
        """
        # 1. Шукаємо того, хто робить запит, у цій компанії
        requesting_member = await self._member_repo. get_membership_by_company_and_user(
            company_id=company_id,
            user_id=requesting_user_id
        )

        if not requesting_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this company"
            )

        # 2. Перевіряємо права (Якщо не адмін/оунер і не перевіряє сам себе — відмовляємо)
        # Якщо у тебе використовуються Enum, заміни тут рядки на CompanyRole.ADMIN тощо
        if requesting_member.role not in ["admin", "owner"] and requesting_user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only company admins or owners can view other members' scores"
            )

        # 3. Якщо все ок — робимо запит до репозиторію результатів
        return await self._quiz_result_repo.get_average_score(
            user_id=user_id,
            company_id=company_id
        )
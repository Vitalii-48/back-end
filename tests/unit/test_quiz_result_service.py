from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.enums import CompanyRole
from app.repositories.quiz_cache_repository import QuizCacheRepository
from app.services.quiz_result_service import QuizWorkflowService


# ---------- Fixtures ----------

@pytest.fixture
def quiz_repo_mock():
    return AsyncMock()


@pytest.fixture
def quiz_result_repo_mock():
    return AsyncMock()


@pytest.fixture
def member_repo_mock():
    return AsyncMock()


@pytest.fixture
def user_repo_mock():
    return AsyncMock()


@pytest.fixture
def quiz_cache_repo_mock():
    return AsyncMock(spec=QuizCacheRepository)


@pytest.fixture
def service(
        quiz_repo_mock,
        quiz_result_repo_mock,
        member_repo_mock,
        user_repo_mock,
        quiz_cache_repo_mock,
):
    return QuizWorkflowService(
        quiz_repo=quiz_repo_mock,
        quiz_result_repo=quiz_result_repo_mock,
        member_repo=member_repo_mock,
        user_repo=user_repo_mock,
        quiz_cache_repo=quiz_cache_repo_mock,
    )


# ---------- Helpers ----------

def make_option(option_id=None, is_correct=False):
    option = MagicMock()
    option.id = option_id or uuid4()
    option.is_correct = is_correct
    return option


def make_question(question_id=None, options=None):
    question = MagicMock()
    question.id = question_id or uuid4()
    question.options = options or []
    return question


def make_quiz(quiz_id=None, company_id=None, questions=None):
    quiz = MagicMock()
    quiz.id = quiz_id or uuid4()
    quiz.company_id = company_id or uuid4()
    quiz.questions = questions or []
    return quiz


def make_payload(answers):
    payload = MagicMock()
    payload.answers = answers
    return payload


def make_answer(question_id, selected_option_ids):
    answer = MagicMock()
    answer.question_id = question_id
    answer.selected_option_ids = selected_option_ids
    return answer


def make_member(role=CompanyRole.MEMBER):
    member = MagicMock()
    member.role = role
    return member


# ============================================================
# submit_quiz
# ============================================================

class TestSubmitQuiz:
    @pytest.mark.asyncio
    async def test_submit_quiz_quiz_not_found(self, service, quiz_repo_mock):
        quiz_repo_mock.get_quiz_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            await service.submit_quiz(
                company_id=uuid4(),
                quiz_id=uuid4(),
                user_id=uuid4(),
                payload=make_payload([]),
            )

        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_submit_quiz_wrong_company(self, service, quiz_repo_mock):
        quiz = make_quiz(company_id=uuid4())
        quiz_repo_mock.get_quiz_by_id.return_value = quiz

        with pytest.raises(HTTPException) as exc:
            await service.submit_quiz(
                company_id=uuid4(),
                quiz_id=quiz.id,
                user_id=uuid4(),
                payload=make_payload([]),
            )

        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_submit_quiz_forbidden_for_non_member(
            self, service, quiz_repo_mock, member_repo_mock
    ):
        company_id = uuid4()
        quiz = make_quiz(company_id=company_id)

        quiz_repo_mock.get_quiz_by_id.return_value = quiz

        # Підганяємо під назви методів у вашому QuizWorkflowService
        member_repo_mock.get_membership_by_company_and_user.return_value = None
        member_repo_mock.get_member.return_value = None

        with pytest.raises(HTTPException) as exc:
            await service.submit_quiz(
                company_id=company_id,
                quiz_id=quiz.id,
                user_id=uuid4(),
                payload=make_payload([]),
            )

        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_submit_quiz_success_all_correct(
            self, service, quiz_repo_mock, member_repo_mock, quiz_result_repo_mock, quiz_cache_repo_mock
    ):
        company_id = uuid4()

        correct_option_id = uuid4()
        option = make_option(option_id=correct_option_id, is_correct=True)
        question = make_question(options=[option])
        quiz = make_quiz(company_id=company_id, questions=[question])

        quiz_repo_mock.get_quiz_by_id.return_value = quiz
        member_repo_mock.get_membership_by_company_and_user.return_value = make_member()
        member_repo_mock.get_member.return_value = make_member()

        result_mock = MagicMock()
        result_mock.id = uuid4()
        result_mock.user_id = uuid4()
        result_mock.quiz_id = quiz.id
        result_mock.correct_answers_count = 1
        result_mock.total_questions_count = 1
        result_mock.score = 1.0
        quiz_result_repo_mock.create_result.return_value = result_mock

        answer = make_answer(question.id, [correct_option_id])
        payload = make_payload([answer])

        result = await service.submit_quiz(
            company_id=company_id,
            quiz_id=quiz.id,
            user_id=uuid4(),
            payload=payload,
        )

        assert result.correct_answers_count == 1
        assert result.total_questions_count == 1
        assert result.is_passed is True
        quiz_result_repo_mock.create_result.assert_awaited_once()
        quiz_repo_mock.increment_frequency.assert_awaited_once()
        quiz_cache_repo_mock.save_quiz_attempt.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_submit_quiz_all_wrong(
            self, service, quiz_repo_mock, member_repo_mock, quiz_result_repo_mock
    ):
        company_id = uuid4()

        correct_option_id = uuid4()
        wrong_option_id = uuid4()
        option = make_option(option_id=correct_option_id, is_correct=True)
        question = make_question(options=[option])
        quiz = make_quiz(company_id=company_id, questions=[question])

        quiz_repo_mock.get_quiz_by_id.return_value = quiz
        member_repo_mock.get_membership_by_company_and_user.return_value = make_member()
        member_repo_mock.get_member.return_value = make_member()

        result_mock = MagicMock()
        result_mock.quiz_id = quiz.id
        result_mock.correct_answers_count = 0
        result_mock.total_questions_count = 1
        result_mock.score = 0.0
        quiz_result_repo_mock.create_result.return_value = result_mock

        answer = make_answer(question.id, [wrong_option_id])
        payload = make_payload([answer])

        result = await service.submit_quiz(
            company_id=company_id,
            quiz_id=quiz.id,
            user_id=uuid4(),
            payload=payload,
        )

        assert result.correct_answers_count == 0


# ============================================================
# get_my_average_score
# ============================================================

class TestGetMyAverageScore:
    @pytest.mark.asyncio
    async def test_get_my_average_score_success(self, service, quiz_result_repo_mock):
        user_id = uuid4()
        quiz_result_repo_mock.get_average_score.return_value = 0.75

        result = await service.get_my_average_score(user_id=user_id)

        assert result == 0.75
        quiz_result_repo_mock.get_average_score.assert_awaited_once_with(
            user_id=user_id,
            company_id=None,
        )


# ============================================================
# get_user_average_in_company
# ============================================================

class TestGetUserAverageInCompany:
    @pytest.mark.asyncio
    async def test_get_user_average_in_company_forbidden_for_non_member(
            self, service, member_repo_mock
    ):
        member_repo_mock.get_membership_by_company_and_user.return_value = None

        with pytest.raises(HTTPException) as exc:
            await service.get_user_average_in_company(
                user_id=uuid4(),
                company_id=uuid4(),
                requesting_user_id=uuid4(),
            )

        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_user_average_in_company_forbidden_for_regular_member_viewing_others(
            self, service, member_repo_mock
    ):
        member_repo_mock.get_membership_by_company_and_user.return_value = make_member(CompanyRole.MEMBER)

        with pytest.raises(HTTPException) as exc:
            await service.get_user_average_in_company(
                user_id=uuid4(),
                company_id=uuid4(),
                requesting_user_id=uuid4(),
            )

        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_user_average_in_company_allowed_for_admin_viewing_anyone(
            self, service, member_repo_mock, quiz_result_repo_mock
    ):
        # Гарантуємо, що макет роль збігається з перевіркою enum
        admin_member = make_member(CompanyRole.ADMIN)
        member_repo_mock.get_membership_by_company_and_user.return_value = admin_member
        quiz_result_repo_mock.get_average_score.return_value = 0.85

        target_user_id = uuid4()
        company_id = uuid4()

        result = await service.get_user_average_in_company(
            user_id=target_user_id,
            company_id=company_id,
            requesting_user_id=uuid4(),
        )

        assert result == 0.85
        quiz_result_repo_mock.get_average_score.assert_awaited_once_with(
            user_id=target_user_id,
            company_id=company_id,
        )

    @pytest.mark.asyncio
    async def test_get_user_average_in_company_allowed_for_self_viewing(
            self, service, member_repo_mock, quiz_result_repo_mock
    ):
        member_repo_mock.get_membership_by_company_and_user.return_value = make_member(CompanyRole.MEMBER)
        quiz_result_repo_mock.get_average_score.return_value = 0.60

        same_user_id = uuid4()
        company_id = uuid4()

        result = await service.get_user_average_in_company(
            user_id=same_user_id,
            company_id=company_id,
            requesting_user_id=same_user_id,
        )

        assert result == 0.60
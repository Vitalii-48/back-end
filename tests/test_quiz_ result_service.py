# tests/test_quiz_result_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import HTTPException
from app.services.quiz_result_service import QuizWorkflowService


# ─── Helpers ────────────────────────────────────────────────────────────────

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


def make_service():
    service = QuizWorkflowService(
        quiz_repo=AsyncMock(),
        quiz_result_repo=AsyncMock(),
        member_repo=AsyncMock(),
        user_repo=AsyncMock(),
    )
    return service


def make_payload(answers):
    payload = MagicMock()
    payload.answers = answers
    return payload


def make_answer(question_id, selected_option_ids):
    answer = MagicMock()
    answer.question_id = question_id
    answer.selected_option_ids = selected_option_ids
    return answer


# ─── Tests: submit_quiz ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_submit_quiz_quiz_not_found():
    service = make_service()
    service._quiz_repo.get_quiz_by_id.return_value = None

    with pytest.raises(HTTPException) as exc:
        await service.submit_quiz(
            company_id=uuid4(),
            quiz_id=uuid4(),
            user_id=uuid4(),
            payload=make_payload([]),
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_submit_quiz_wrong_company():
    service = make_service()
    quiz = make_quiz(company_id=uuid4())
    service._quiz_repo.get_quiz_by_id.return_value = quiz

    with pytest.raises(HTTPException) as exc:
        await service.submit_quiz(
            company_id=uuid4(),  # інша компанія
            quiz_id=quiz.id,
            user_id=uuid4(),
            payload=make_payload([]),
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_submit_quiz_not_a_member():
    service = make_service()
    company_id = uuid4()
    quiz = make_quiz(company_id=company_id)

    service._quiz_repo.get_quiz_by_id.return_value = quiz
    service._member_repo.get_member.return_value = None  # не член

    with pytest.raises(HTTPException) as exc:
        await service.submit_quiz(
            company_id=company_id,
            quiz_id=quiz.id,
            user_id=uuid4(),
            payload=make_payload([]),
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_submit_quiz_all_correct():
    service = make_service()
    company_id = uuid4()

    # Питання з одним правильним варіантом
    correct_option_id = uuid4()
    option = make_option(option_id=correct_option_id, is_correct=True)
    question = make_question(options=[option])
    quiz = make_quiz(company_id=company_id, questions=[question])

    service._quiz_repo.get_quiz_by_id.return_value = quiz
    service._member_repo.get_member.return_value = MagicMock()

    result_mock = MagicMock()
    result_mock.id = uuid4()
    result_mock.user_id = uuid4()
    result_mock.quiz_id = quiz.id
    result_mock.correct_answers_count = 1
    result_mock.total_questions_count = 1
    result_mock.score = 1.0
    service._quiz_result_repo.create_result.return_value = result_mock

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
    service._quiz_result_repo.create_result.assert_called_once()
    service._user_repo.update_last_attempt.assert_called_once()
    service._quiz_repo.increment_frequency.assert_called_once()


@pytest.mark.asyncio
async def test_submit_quiz_all_wrong():
    service = make_service()
    company_id = uuid4()

    correct_option_id = uuid4()
    wrong_option_id = uuid4()
    option = make_option(option_id=correct_option_id, is_correct=True)
    question = make_question(options=[option])
    quiz = make_quiz(company_id=company_id, questions=[question])

    service._quiz_repo.get_quiz_by_id.return_value = quiz
    service._member_repo.get_member.return_value = MagicMock()

    result_mock = MagicMock()
    result_mock.quiz_id = quiz.id
    result_mock.correct_answers_count = 0
    result_mock.total_questions_count = 1
    result_mock.score = 0.0
    service._quiz_result_repo.create_result.return_value = result_mock

    # Юзер вибрав неправильний варіант
    answer = make_answer(question.id, [wrong_option_id])
    payload = make_payload([answer])

    result = await service.submit_quiz(
        company_id=company_id,
        quiz_id=quiz.id,
        user_id=uuid4(),
        payload=payload,
    )

    assert result.correct_answers_count == 0


# ─── Tests: get_my_average_score ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_my_average_score():
    service = make_service()
    user_id = uuid4()
    service._quiz_result_repo.get_average_score.return_value = 0.75

    result = await service.get_my_average_score(user_id=user_id)

    assert result == 0.75
    service._quiz_result_repo.get_average_score.assert_called_once_with(
        user_id=user_id,
        company_id=None,
    )


# ─── Tests: get_user_average_in_company ─────────────────────────────────────

@pytest.mark.asyncio
async def test_get_user_average_not_a_member():
    service = make_service()
    service._member_repo.get_member.return_value = None

    with pytest.raises(HTTPException) as exc:
        await service.get_user_average_in_company(
            user_id=uuid4(),
            company_id=uuid4(),
            requesting_user_id=uuid4(),
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_user_average_non_admin_cannot_view_others():
    service = make_service()

    member = MagicMock()
    member.role = "member"  # не admin/owner
    service._member_repo.get_member.return_value = member

    with pytest.raises(HTTPException) as exc:
        await service.get_user_average_in_company(
            user_id=uuid4(),           # чужий user_id
            company_id=uuid4(),
            requesting_user_id=uuid4(),  # інший юзер
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_user_average_admin_can_view_anyone():
    service = make_service()

    # Той, хто запитує — адмін
    requesting_member = MagicMock()
    requesting_member.role = "admin"
    service._member_repo.get_member.return_value = requesting_member

    # Репозиторій повертає якийсь бал
    service._quiz_result_repo.get_average_score.return_value = 0.85

    target_user_id = uuid4()
    company_id = uuid4()

    result = await service.get_user_average_in_company(
        user_id=target_user_id,
        company_id=company_id,
        requesting_user_id=uuid4(),  # ID адміна
    )

    assert result == 0.85
    service._quiz_result_repo.get_average_score.assert_called_once_with(
        user_id=target_user_id,
        company_id=company_id,
    )


@pytest.mark.asyncio
async def test_get_user_average_user_can_view_themselves():
    service = make_service()

    # Звичайний користувач
    requesting_member = MagicMock()
    requesting_member.role = "member"
    service._member_repo.get_member.return_value = requesting_member
    service._quiz_result_repo.get_average_score.return_value = 0.60

    same_user_id = uuid4()
    company_id = uuid4()

    # user_id та requesting_user_id збігаються (юзер дивиться свій бал)
    result = await service.get_user_average_in_company(
        user_id=same_user_id,
        company_id=company_id,
        requesting_user_id=same_user_id,
    )

    assert result == 0.60
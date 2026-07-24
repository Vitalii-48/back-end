from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.enums import CompanyRole
from app.schemas.quiz import (
    QuizAnswerOptionCreate,
    QuizCreateRequest,
    QuizQuestionCreate,
    QuizUpdateRequest,
)
from app.services.quiz_service import QuizService


# ---------- Fixtures (спільні для всіх тестів) ----------

@pytest.fixture
def quiz_repo_mock():
    return AsyncMock()


@pytest.fixture
def member_repo_mock():
    return AsyncMock()


@pytest.fixture
def company_repo_mock():
    return AsyncMock()


@pytest.fixture
def notification_service_mock():
    return AsyncMock()


@pytest.fixture
def service(
    quiz_repo_mock,
    member_repo_mock,
    company_repo_mock,
    notification_service_mock,
):
    return QuizService(
        quiz_repo=quiz_repo_mock,
        member_repo=member_repo_mock,
        company_repo=company_repo_mock,
        notification_service=notification_service_mock,
    )


# ---------- Допоміжні функції (Factories) ----------

def make_membership(role=CompanyRole.MEMBER):
    return SimpleNamespace(role=role)


def make_option(is_correct=False):
    return SimpleNamespace(id=uuid4(), text="Answer", is_correct=is_correct)


def make_question_response():
    return SimpleNamespace(
        id=uuid4(),
        title="Question title",
        options=[
            make_option(is_correct=True),
            make_option(is_correct=False),
        ],
    )


def make_quiz(company_id=None):
    return SimpleNamespace(
        id=uuid4(),
        company_id=company_id or uuid4(),
        title="Quiz title",
        description="Quiz description",
        frequency=0,
        questions=[make_question_response(), make_question_response()],
    )


def create_options(first_correct=True, second_correct=False):
    return [
        QuizAnswerOptionCreate(text="A", is_correct=first_correct),
        QuizAnswerOptionCreate(text="B", is_correct=second_correct),
    ]


def create_question(title="Question title", options=None):
    return QuizQuestionCreate(
        title=title,
        options=options or create_options(),
    )


def make_quiz_payload():
    return QuizCreateRequest(
        title="Python quiz",
        description="Basic quiz",
        questions=[
            create_question("First question"),
            create_question(
                "Second question",
                create_options(first_correct=False, second_correct=True),
            ),
        ],
    )


# ============================================================
# create_company_quiz
# ============================================================

class TestCreateCompanyQuiz:
    @pytest.mark.asyncio
    async def test_create_company_quiz_allowed_for_owner(
            self, service, member_repo_mock, quiz_repo_mock, company_repo_mock, notification_service_mock
    ):
        company_id = uuid4()
        user_id = uuid4()
        quiz = make_quiz(company_id)
        member_ids = [uuid4(), uuid4()]

        member_repo_mock.get_membership_by_company_and_user.return_value = make_membership(CompanyRole.OWNER)
        quiz_repo_mock.create_quiz.return_value = quiz
        company_repo_mock.get_company_by_id.return_value = SimpleNamespace(name="Test Co")
        member_repo_mock.get_all_member_user_ids.return_value = member_ids

        result = await service.create_company_quiz(
            company_id,
            make_quiz_payload(),
            user_id,
        )

        assert result.id == quiz.id
        assert result.company_id == company_id
        quiz_repo_mock.create_quiz.assert_awaited_once()

        notification_service_mock.notify_company_about_new_quiz.assert_awaited_once_with(
            member_ids=member_ids,
            company_name="Test Co",
            quiz_title=quiz.title,
        )

    @pytest.mark.asyncio
    async def test_create_company_quiz_does_not_notify_when_no_members(
            self, service, member_repo_mock, quiz_repo_mock, company_repo_mock, notification_service_mock
    ):
        """Якщо в компанії немає учасників — сповіщення взагалі не надсилається (if member_ids)."""
        company_id = uuid4()
        quiz = make_quiz(company_id)

        member_repo_mock.get_membership_by_company_and_user.return_value = make_membership(CompanyRole.OWNER)
        quiz_repo_mock.create_quiz.return_value = quiz
        company_repo_mock.get_company_by_id.return_value = SimpleNamespace(name="Empty Co")
        member_repo_mock.get_all_member_user_ids.return_value = []  # немає учасників

        await service.create_company_quiz(company_id, make_quiz_payload(), uuid4())

        notification_service_mock.notify_company_about_new_quiz.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_company_quiz_company_not_found(
            self, service, member_repo_mock, company_repo_mock
    ):
        member_repo_mock.get_membership_by_company_and_user.return_value = make_membership(CompanyRole.OWNER)
        company_repo_mock.get_company_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            await service.create_company_quiz(uuid4(), make_quiz_payload(), uuid4())

        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_create_company_quiz_allowed_for_admin(
        self, service, member_repo_mock, quiz_repo_mock
    ):
        company_id = uuid4()
        user_id = uuid4()
        quiz = make_quiz(company_id)

        member_repo_mock.get_membership_by_company_and_user.return_value = make_membership(CompanyRole.ADMIN)
        quiz_repo_mock.create_quiz.return_value = quiz

        result = await service.create_company_quiz(
            company_id,
            make_quiz_payload(),
            user_id,
        )

        assert result.company_id == company_id
        quiz_repo_mock.create_quiz.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_company_quiz_forbidden_for_regular_member(
        self, service, member_repo_mock, quiz_repo_mock
    ):
        member_repo_mock.get_membership_by_company_and_user.return_value = make_membership(CompanyRole.MEMBER)

        with pytest.raises(HTTPException) as exc:
            await service.create_company_quiz(
                uuid4(),
                make_quiz_payload(),
                uuid4(),
            )

        assert exc.value.status_code == 403
        quiz_repo_mock.create_quiz.assert_not_awaited()


# ============================================================
# get_company_quizzes_list
# ============================================================

class TestGetCompanyQuizzesList:
    @pytest.mark.asyncio
    async def test_get_company_quizzes_list_success_for_member(
        self, service, member_repo_mock, quiz_repo_mock
    ):
        company_id = uuid4()
        quiz = make_quiz(company_id)

        member_repo_mock.get_membership_by_company_and_user.return_value = make_membership(CompanyRole.MEMBER)
        quiz_repo_mock.get_company_quizzes.return_value = ([quiz], 1)

        result = await service.get_company_quizzes_list(
            company_id,
            uuid4(),
            page=1,
            per_page=10,
        )

        assert result.total == 1
        assert len(result.quizzes) == 1
        quiz_repo_mock.get_company_quizzes.assert_awaited_once_with(
            company_id=company_id,
            skip=0,
            limit=10,
        )

    @pytest.mark.asyncio
    async def test_get_company_quizzes_list_forbidden_for_non_member(
        self, service, member_repo_mock, quiz_repo_mock
    ):
        member_repo_mock.get_membership_by_company_and_user.return_value = None

        with pytest.raises(HTTPException) as exc:
            await service.get_company_quizzes_list(
                uuid4(),
                uuid4(),
                page=1,
                per_page=10,
            )

        assert exc.value.status_code == 403
        quiz_repo_mock.get_company_quizzes.assert_not_awaited()


# ============================================================
# update_company_quiz & delete_company_quiz
# ============================================================

class TestUpdateAndDeleteCompanyQuiz:
    @pytest.mark.asyncio
    async def test_update_company_quiz_allowed_for_admin(
        self, service, member_repo_mock, quiz_repo_mock
    ):
        company_id = uuid4()
        quiz = make_quiz(company_id)

        member_repo_mock.get_membership_by_company_and_user.return_value = make_membership(CompanyRole.ADMIN)
        quiz_repo_mock.get_quiz_by_id.return_value = quiz
        quiz_repo_mock.update_quiz.return_value = quiz

        result = await service.update_company_quiz(
            quiz_id=quiz.id,
            company_id=company_id,
            data=QuizUpdateRequest(title="Updated quiz"),
            user_id=uuid4(),
        )

        assert result.id == quiz.id
        quiz_repo_mock.update_quiz.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_company_quiz_allowed_for_admin(
        self, service, member_repo_mock, quiz_repo_mock
    ):
        company_id = uuid4()
        quiz = make_quiz(company_id)

        member_repo_mock.get_membership_by_company_and_user.return_value = make_membership(CompanyRole.ADMIN)
        quiz_repo_mock.get_quiz_by_id.return_value = quiz

        await service.delete_company_quiz(
            quiz.id,
            company_id,
            uuid4(),
        )

        quiz_repo_mock.delete_quiz.assert_awaited_once_with(quiz)


# ============================================================
# QuizCreateRequest — валідація схеми (Pydantic), без мокінгу сервісу
# ============================================================

def test_quiz_requires_at_least_two_questions():
    with pytest.raises(ValueError):
        QuizCreateRequest(
            title="Bad quiz",
            description="Too few questions",
            questions=[
                create_question("Only question"),
            ],
        )


def test_question_requires_two_to_four_options():
    with pytest.raises(ValueError):
        QuizCreateRequest(
            title="Bad quiz",
            description="Too few options",
            questions=[
                create_question(
                    "First question",
                    [QuizAnswerOptionCreate(text="A", is_correct=True)],
                ),
                create_question("Second question"),
            ],
        )


def test_question_requires_at_least_one_correct_answer():
    with pytest.raises(ValueError):
        QuizCreateRequest(
            title="Bad quiz",
            description="No correct answer",
            questions=[
                create_question(
                    "First question",
                    create_options(first_correct=False, second_correct=False),
                ),
                create_question("Second question"),
            ],
        )


def test_question_allows_multiple_correct_answers():
    payload = QuizCreateRequest(
        title="Good quiz",
        description="Multiple correct answers",
        questions=[
            create_question(
                "First question",
                create_options(first_correct=True, second_correct=True),
            ),
            create_question("Second question"),
        ],
    )

    assert payload.questions[0].options[0].is_correct is True
    assert payload.questions[0].options[1].is_correct is True
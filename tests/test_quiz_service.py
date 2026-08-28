import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import HTTPException

from app.models.enums import CompanyRole
from app.schemas.quiz import (
    QuizAnswerOptionCreate,
    QuizCreateRequest,
    QuizQuestionCreate,
    QuizUpdateRequest,
)
from app.services.quiz_service import QuizService


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


def make_service():
    quiz_repo = AsyncMock()
    member_repo = AsyncMock()
    company_repo = AsyncMock()

    create_quiz_mock = AsyncMock()
    get_company_quizzes_mock = AsyncMock()
    get_quiz_by_id_mock = AsyncMock()
    update_quiz_mock = AsyncMock()
    delete_quiz_mock = AsyncMock()
    get_membership_mock = AsyncMock()

    quiz_repo.create_quiz = create_quiz_mock
    quiz_repo.get_company_quizzes = get_company_quizzes_mock
    quiz_repo.get_quiz_by_id = get_quiz_by_id_mock
    quiz_repo.update_quiz = update_quiz_mock
    quiz_repo.delete_quiz = delete_quiz_mock
    member_repo.get_membership_by_company_and_user = get_membership_mock

    service = QuizService(
        quiz_repo=quiz_repo,
        member_repo=member_repo,
        company_repo=company_repo,
    )

    return service, {
        "create_quiz": create_quiz_mock,
        "get_company_quizzes": get_company_quizzes_mock,
        "get_quiz_by_id": get_quiz_by_id_mock,
        "update_quiz": update_quiz_mock,
        "delete_quiz": delete_quiz_mock,
        "get_membership": get_membership_mock,
    }


@pytest.mark.asyncio
async def test_owner_can_create_quiz():
    service, mocks = make_service()
    company_id = uuid4()
    user_id = uuid4()
    quiz = make_quiz(company_id)

    mocks["get_membership"].return_value = make_membership(CompanyRole.OWNER)
    mocks["create_quiz"].return_value = quiz

    result = await service.create_company_quiz(
        company_id,
        make_quiz_payload(),
        user_id,
    )

    assert result.id == quiz.id
    assert result.company_id == company_id
    mocks["create_quiz"].assert_called_once()


@pytest.mark.asyncio
async def test_admin_can_create_quiz():
    service, mocks = make_service()
    company_id = uuid4()
    user_id = uuid4()
    quiz = make_quiz(company_id)

    mocks["get_membership"].return_value = make_membership(CompanyRole.ADMIN)
    mocks["create_quiz"].return_value = quiz

    result = await service.create_company_quiz(
        company_id,
        make_quiz_payload(),
        user_id,
    )

    assert result.company_id == company_id
    mocks["create_quiz"].assert_called_once()


@pytest.mark.asyncio
async def test_member_cannot_create_quiz():
    service, mocks = make_service()

    mocks["get_membership"].return_value = make_membership(CompanyRole.MEMBER)

    with pytest.raises(HTTPException) as exc:
        await service.create_company_quiz(
            uuid4(),
            make_quiz_payload(),
            uuid4(),
        )

    assert exc.value.status_code == 403
    mocks["create_quiz"].assert_not_called()


@pytest.mark.asyncio
async def test_member_can_get_quizzes_list():
    service, mocks = make_service()
    company_id = uuid4()
    quiz = make_quiz(company_id)

    mocks["get_membership"].return_value = make_membership(CompanyRole.MEMBER)
    mocks["get_company_quizzes"].return_value = ([quiz], 1)

    result = await service.get_company_quizzes_list(
        company_id,
        uuid4(),
        page=1,
        size=10,
    )

    assert result.total == 1
    assert len(result.quizzes) == 1
    mocks["get_company_quizzes"].assert_called_once_with(
        company_id=company_id,
        skip=0,
        limit=10,
    )


@pytest.mark.asyncio
async def test_non_member_cannot_get_quizzes_list():
    service, mocks = make_service()

    mocks["get_membership"].return_value = None

    with pytest.raises(HTTPException) as exc:
        await service.get_company_quizzes_list(
            uuid4(),
            uuid4(),
            page=1,
            size=10,
        )

    assert exc.value.status_code == 403
    mocks["get_company_quizzes"].assert_not_called()


@pytest.mark.asyncio
async def test_admin_can_update_quiz():
    service, mocks = make_service()
    company_id = uuid4()
    quiz = make_quiz(company_id)

    mocks["get_membership"].return_value = make_membership(CompanyRole.ADMIN)
    mocks["get_quiz_by_id"].return_value = quiz
    mocks["update_quiz"].return_value = quiz

    result = await service.update_company_quiz(
        quiz_id=quiz.id,
        company_id=company_id,
        data=QuizUpdateRequest(title="Updated quiz"),
        user_id=uuid4(),
    )

    assert result.id == quiz.id
    mocks["update_quiz"].assert_called_once()


@pytest.mark.asyncio
async def test_admin_can_delete_quiz():
    service, mocks = make_service()
    company_id = uuid4()
    quiz = make_quiz(company_id)

    mocks["get_membership"].return_value = make_membership(CompanyRole.ADMIN)
    mocks["get_quiz_by_id"].return_value = quiz

    await service.delete_company_quiz(
        quiz.id,
        company_id,
        uuid4(),
    )

    mocks["delete_quiz"].assert_called_once_with(quiz)


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
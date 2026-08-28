# tests/unit/test_quiz_import_service.py
import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.services.quiz_import_service import QuizImportService
from app.schemas.quiz_import import ParsedQuizData, ParsedQuestionData, ParsedAnswerData
from app.models.enums import CompanyRole


def make_service():
    svc = QuizImportService.__new__(QuizImportService)  # type: ignore
    svc.quiz_repo = AsyncMock()
    svc.quiz_repo.session = AsyncMock()
    svc.member_repo = AsyncMock()
    svc.company_repo = AsyncMock()
    svc.company_repo.get_company_by_id.return_value = AsyncMock()
    return svc


def make_valid_quiz_data(title="Python Basics") -> ParsedQuizData:
    return ParsedQuizData(
        title=title,
        description="desc",
        frequency=24,
        questions=[
            ParsedQuestionData(title="Q1", answers=[
                ParsedAnswerData(text="A", is_correct=True),
                ParsedAnswerData(text="B", is_correct=False),
            ]),
            ParsedQuestionData(title="Q2", answers=[
                ParsedAnswerData(text="A", is_correct=False),
                ParsedAnswerData(text="B", is_correct=True),
            ]),
        ],
    )


@pytest.mark.asyncio
async def test_import_rejects_company_not_found(monkeypatch):
    """
    Перевіряє порядок '404 перед 403': якщо компанії не існує,
    має кинутись 404, а не 403 — навіть якщо права взагалі не перевірялись.
    """
    svc = make_service()
    company_id, user_id = uuid.uuid4(), uuid.uuid4()

    svc.company_repo.get_company_by_id.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await svc.import_quizzes(company_id, b"fake-bytes", user_id)

    assert exc_info.value.status_code == 404
    # Перевірка ролі не мала навіть викликатись — компанія "впала" раніше
    svc.member_repo.get_membership_by_company_and_user.assert_not_called()
    svc.quiz_repo.create_with_questions.assert_not_called()


@pytest.mark.asyncio
async def test_import_rejects_non_admin(monkeypatch):
    svc = make_service()
    company_id, user_id = uuid.uuid4(), uuid.uuid4()

    membership = AsyncMock()
    membership.role = CompanyRole.MEMBER
    svc.member_repo.get_membership_by_company_and_user.return_value = membership

    with pytest.raises(HTTPException) as exc_info:
        await svc.import_quizzes(company_id, b"fake-bytes", user_id)

    assert exc_info.value.status_code == 403
    svc.quiz_repo.create_with_questions.assert_not_called()


@pytest.mark.asyncio
async def test_import_creates_new_quiz(monkeypatch):
    svc = make_service()
    company_id, user_id = uuid.uuid4(), uuid.uuid4()

    membership = AsyncMock()
    membership.role = CompanyRole.ADMIN
    svc.member_repo.get_membership_by_company_and_user.return_value = membership

    quiz_data = make_valid_quiz_data()
    monkeypatch.setattr(
        "app.services.quiz_import_service.parse_excel_to_quizzes",
        lambda content: ([quiz_data], []),
    )
    svc.quiz_repo.get_by_title_and_company.return_value = None

    report = await svc.import_quizzes(company_id, b"fake-bytes", user_id)

    assert report.created == ["Python Basics"]
    assert report.errors == []
    svc.quiz_repo.create_with_questions.assert_called_once_with(company_id, quiz_data)
    svc.quiz_repo.session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_import_updates_existing_quiz(monkeypatch):
    svc = make_service()
    company_id, user_id = uuid.uuid4(), uuid.uuid4()
    existing_quiz = AsyncMock()

    membership = AsyncMock()
    membership.role = CompanyRole.OWNER
    svc.member_repo.get_membership_by_company_and_user.return_value = membership

    quiz_data = make_valid_quiz_data()
    monkeypatch.setattr(
        "app.services.quiz_import_service.parse_excel_to_quizzes",
        lambda content: ([quiz_data], []),
    )
    svc.quiz_repo.get_by_title_and_company.return_value = existing_quiz

    report = await svc.import_quizzes(company_id, b"fake-bytes", user_id)

    assert report.updated == ["Python Basics"]
    svc.quiz_repo.update_with_questions.assert_called_once_with(existing_quiz, quiz_data)


@pytest.mark.asyncio
async def test_import_skips_invalid_quiz(monkeypatch):
    svc = make_service()
    company_id, user_id = uuid.uuid4(), uuid.uuid4()

    membership = AsyncMock()
    membership.role = CompanyRole.ADMIN
    svc.member_repo.get_membership_by_company_and_user.return_value = membership

    invalid_quiz = ParsedQuizData(
        title="Bad Quiz", frequency=24,
        questions=[ParsedQuestionData(title="Only one question", answers=[
            ParsedAnswerData(text="A", is_correct=True),
        ])],
    )
    monkeypatch.setattr(
        "app.services.quiz_import_service.parse_excel_to_quizzes",
        lambda content: ([invalid_quiz], []),
    )

    report = await svc.import_quizzes(company_id, b"fake-bytes", user_id)

    assert report.created == []
    assert len(report.errors) >= 1
    svc.quiz_repo.create_with_questions.assert_not_called()
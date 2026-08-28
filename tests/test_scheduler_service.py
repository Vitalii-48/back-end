# tests/test_scheduler.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.scheduler_service import SchedulerService
from app.repositories.scheduler_repository import SchedulerRepository


# ─── Helpers ────────────────────────────────────────────────────────────────

def make_missed_record(user_id=None, company_name="Test Company", quiz_title="Python Advanced"):
    return user_id or uuid4(), company_name, quiz_title


def make_scheduler_service(scheduler_repo=None, notification_repo=None, session=None):
    """
    Створює SchedulerService з підмоканими репозиторіями та сесією.
    Патчить класи репозиторіїв усередині модуля сервісу так само,
    як вони реально створюються в check_and_notify_missing_quiz_participants().
    """
    session = session or AsyncMock()
    scheduler_repo = scheduler_repo or AsyncMock()
    notification_repo = notification_repo or AsyncMock()

    session_factory = MagicMock()
    session_factory.return_value.__aenter__.return_value = session

    patcher_scheduler_repo = patch(
        "app.services.scheduler_service.SchedulerRepository", return_value=scheduler_repo
    )
    patcher_notification_repo = patch(
        "app.services.scheduler_service.NotificationRepository", return_value=notification_repo
    )
    patcher_scheduler_repo.start()
    patcher_notification_repo.start()

    service = SchedulerService(session_factory=session_factory)
    return service, scheduler_repo, notification_repo, session


def make_scheduler_repository(session=None):
    session = session or AsyncMock()
    return SchedulerRepository(session=session), session


# ─── Tests: SchedulerService.check_and_notify_missing_quiz_participants ─────

@pytest.mark.asyncio
async def test_service_sends_notifications_when_records_found():
    service, scheduler_repo, notification_repo, _ = make_scheduler_service()

    user_id = uuid4()
    scheduler_repo.get_users_who_missed_quizzes.return_value = [
        make_missed_record(user_id, "Test Company", "Python Advanced")
    ]

    await service.check_and_notify_missing_quiz_participants()

    scheduler_repo.get_users_who_missed_quizzes.assert_awaited_once()

    expected_message = (
        "Нагадування: Ви не пройшли квіз 'Python Advanced' "
        "у компанії 'Test Company' за останні 24 години!"
    )
    notification_repo.create_many.assert_awaited_once_with(
        [{"user_id": user_id, "message": expected_message}]
    )


@pytest.mark.asyncio
async def test_service_batches_multiple_records_into_single_call():
    service, scheduler_repo, notification_repo, _ = make_scheduler_service()

    user_id_1, user_id_2 = uuid4(), uuid4()
    scheduler_repo.get_users_who_missed_quizzes.return_value = [
        make_missed_record(user_id_1, "Company A", "Quiz 1"),
        make_missed_record(user_id_2, "Company B", "Quiz 2"),
    ]

    await service.check_and_notify_missing_quiz_participants()

    # Захист від регресії N+1: рівно один виклик create_many з усіма записами
    notification_repo.create_many.assert_awaited_once()
    call_args = notification_repo.create_many.call_args[0][0]
    assert len(call_args) == 2
    assert {item["user_id"] for item in call_args} == {user_id_1, user_id_2}


@pytest.mark.asyncio
async def test_service_does_not_send_notifications_when_no_records():
    service, scheduler_repo, notification_repo, _ = make_scheduler_service()
    scheduler_repo.get_users_who_missed_quizzes.return_value = []

    await service.check_and_notify_missing_quiz_participants()

    scheduler_repo.get_users_who_missed_quizzes.assert_awaited_once()
    notification_repo.create_many.assert_not_awaited()


# ─── Tests: SchedulerRepository.get_users_who_missed_quizzes ────────────────

@pytest.mark.asyncio
async def test_repository_returns_data_from_execute_result():
    repository, session = make_scheduler_repository()

    user_id = uuid4()
    expected_rows = [(user_id, "Test Company", "Python Advanced")]
    mock_result = MagicMock()
    mock_result.all.return_value = expected_rows
    session.execute.return_value = mock_result

    result = await repository.get_users_who_missed_quizzes()

    session.execute.assert_awaited_once()
    assert result == expected_rows


@pytest.mark.asyncio
async def test_repository_returns_empty_list_when_no_missed_quizzes():
    repository, session = make_scheduler_repository()

    mock_result = MagicMock()
    mock_result.all.return_value = []
    session.execute.return_value = mock_result

    result = await repository.get_users_who_missed_quizzes()

    session.execute.assert_awaited_once()
    assert result == []


@pytest.mark.asyncio
async def test_repository_executes_exactly_one_query():
    repository, session = make_scheduler_repository()

    mock_result = MagicMock()
    mock_result.all.return_value = []
    session.execute.return_value = mock_result

    await repository.get_users_who_missed_quizzes()

    assert session.execute.call_count == 1
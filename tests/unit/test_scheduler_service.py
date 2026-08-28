from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.scheduler_service import SchedulerService


# ---------- Fixtures ----------

@pytest.fixture
def scheduler_repo_mock():
    return AsyncMock()


@pytest.fixture
def notification_repo_mock():
    return AsyncMock()


@pytest.fixture
def session_mock():
    return AsyncMock()


@pytest.fixture
def session_factory_mock(session_mock):
    factory = MagicMock()
    factory.return_value.__aenter__.return_value = session_mock
    return factory


# ---------- Helpers ----------

def make_missed_record(user_id=None, company_name="Test Company", quiz_title="Python Advanced"):
    return user_id or uuid4(), company_name, quiz_title


# ---------- Tests ----------

@pytest.mark.asyncio
async def test_check_and_notify_sends_notifications_when_records_found(
    session_factory_mock, scheduler_repo_mock, notification_repo_mock
):
    user_id = uuid4()
    scheduler_repo_mock.get_users_who_missed_quizzes.return_value = [
        make_missed_record(user_id, "Test Company", "Python Advanced")
    ]

    with patch(
        "app.services.scheduler_service.SchedulerRepository",
        return_value=scheduler_repo_mock,
    ), patch(
        "app.services.scheduler_service.NotificationRepository",
        return_value=notification_repo_mock,
    ):
        service = SchedulerService(session_factory=session_factory_mock)
        await service.check_and_notify_missing_quiz_participants()

    scheduler_repo_mock.get_users_who_missed_quizzes.assert_awaited_once()

    expected_message = (
        "Нагадування: Ви не пройшли квіз 'Python Advanced' "
        "у компанії 'Test Company' за останні 24 години!"
    )
    notification_repo_mock.create_many.assert_awaited_once_with(
        [{"user_id": user_id, "message": expected_message}]
    )


@pytest.mark.asyncio
async def test_check_and_notify_batches_multiple_records_into_single_call(
    session_factory_mock, scheduler_repo_mock, notification_repo_mock
):
    user_id_1, user_id_2 = uuid4(), uuid4()
    scheduler_repo_mock.get_users_who_missed_quizzes.return_value = [
        make_missed_record(user_id_1, "Company A", "Quiz 1"),
        make_missed_record(user_id_2, "Company B", "Quiz 2"),
    ]

    with patch(
        "app.services.scheduler_service.SchedulerRepository",
        return_value=scheduler_repo_mock,
    ), patch(
        "app.services.scheduler_service.NotificationRepository",
        return_value=notification_repo_mock,
    ):
        service = SchedulerService(session_factory=session_factory_mock)
        await service.check_and_notify_missing_quiz_participants()

    notification_repo_mock.create_many.assert_awaited_once()
    call_args = notification_repo_mock.create_many.call_args[0][0]
    assert len(call_args) == 2
    assert {item["user_id"] for item in call_args} == {user_id_1, user_id_2}


@pytest.mark.asyncio
async def test_check_and_notify_does_not_send_notifications_when_no_records(
    session_factory_mock, scheduler_repo_mock, notification_repo_mock
):
    scheduler_repo_mock.get_users_who_missed_quizzes.return_value = []

    with patch(
        "app.services.scheduler_service.SchedulerRepository",
        return_value=scheduler_repo_mock,
    ), patch(
        "app.services.scheduler_service.NotificationRepository",
        return_value=notification_repo_mock,
    ):
        service = SchedulerService(session_factory=session_factory_mock)
        await service.check_and_notify_missing_quiz_participants()

    scheduler_repo_mock.get_users_who_missed_quizzes.assert_awaited_once()
    notification_repo_mock.create_many.assert_not_awaited()
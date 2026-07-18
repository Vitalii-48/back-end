# tests/test_notification_service.py

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.enums import NotificationStatus
from app.services.notification_service import NotificationService

# ---------- Fixtures (спільні для всіх тестів) ----------

@pytest.fixture
def notification_repo_mock():
    return AsyncMock()


@pytest.fixture
def service(notification_repo_mock):
    return NotificationService(notification_repository=notification_repo_mock)


# ---------- Допоміжні функції для створення тестових даних ----------

def make_notification(notification_id=None, user_id=None, status=NotificationStatus.UNREAD, message="test"):
    """Імітує ORM-об'єкт Notification без реальної SQLAlchemy-моделі."""
    return SimpleNamespace(
        id=notification_id or uuid4(),
        user_id=user_id or uuid4(),
        status=status,
        message=message,
    )


# ============================================================
# notify_company_about_new_quiz
# ============================================================

class TestNotifyCompanyAboutNewQuiz:
    async def test_calls_repo_create_bulk_with_all_member_ids(self, service, notification_repo_mock):
        member_ids = [uuid4(), uuid4(), uuid4()]

        await service.notify_company_about_new_quiz(
            member_ids=member_ids,
            company_name="Test Co",
            quiz_title="Python Basics",
        )

        # create_bulk викликається ПОЗИЦІЙНО: create_bulk(member_ids, message)
        notification_repo_mock.create_bulk.assert_awaited_once()
        call_args = notification_repo_mock.create_bulk.call_args.args
        passed_member_ids, passed_message = call_args
        assert passed_member_ids == member_ids
        assert "Python Basics" in passed_message
        assert "Test Co" in passed_message

    async def test_does_nothing_when_no_members(self, service, notification_repo_mock):
        """
        Якщо список учасників порожній -- сервіс виходить одразу через `if not member_ids: return`
        і НЕ звертається до репозиторію. Це навмисна оптимізація в реальному коді,
        тому перевіряємо саме відсутність виклику.
        """
        await service.notify_company_about_new_quiz(
            member_ids=[],
            company_name="Empty Co",
            quiz_title="Quiz",
        )

        notification_repo_mock.create_bulk.assert_not_awaited()


# ============================================================
# get_user_notifications
# ============================================================

class TestGetUserNotifications:
    async def test_returns_notifications_and_total_from_repo(self, service, notification_repo_mock):
        user_id = uuid4()
        fake_notifications = [make_notification(user_id=user_id), make_notification(user_id=user_id)]
        notification_repo_mock.get_user_notifications_with_count.return_value = (fake_notifications, 2)

        notifications, total = await service.get_user_notifications(user_id=user_id, page=1, per_page=5)

        notification_repo_mock.get_user_notifications_with_count.assert_awaited_once_with(
            user_id=user_id, skip=0, limit=5
        )
        assert notifications == fake_notifications
        assert total == 2

    async def test_uses_default_pagination_values(self, service, notification_repo_mock):
        """Перевіряємо дефолтні skip/limit, якщо їх не передали явно."""
        user_id = uuid4()
        notification_repo_mock.get_user_notifications_with_count.return_value = ([], 0)

        await service.get_user_notifications(user_id=user_id)

        _, kwargs = notification_repo_mock.get_user_notifications_with_count.call_args
        assert kwargs["skip"] == 0
        assert kwargs["limit"] == 10


# ============================================================
# mark_as_read
# ============================================================

class TestMarkAsRead:
    async def test_marks_own_notification_as_read(self, service, notification_repo_mock):
        """
        Мутація статусу (UNREAD -> READ) відбувається всередині РЕПОЗИТОРІЮ,
        а не сервісу -- тут репозиторій замокано, тому реальна мутація не виконується.
        Перевіряємо відповідальність САМЕ сервісу: (1) правильний виклик репозиторію,
        (2) повернення того, що повернув репозиторій.
        """
        user_id = uuid4()
        notification = make_notification(user_id=user_id, status=NotificationStatus.UNREAD)
        already_read = make_notification(
            notification_id=notification.id, user_id=user_id, status=NotificationStatus.READ
        )
        notification_repo_mock.get_by_id.return_value = notification
        notification_repo_mock.mark_as_read.return_value = already_read

        result = await service.mark_as_read(notification.id, current_user_id=user_id)

        notification_repo_mock.mark_as_read.assert_awaited_once_with(notification)
        assert result is already_read
        assert result.status == NotificationStatus.READ

    async def test_raises_404_when_notification_not_found(self, service, notification_repo_mock):
        """404 перед 403: якщо сповіщення взагалі не існує."""
        notification_repo_mock.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            await service.mark_as_read(uuid4(), current_user_id=uuid4())

        assert exc.value.status_code == 404

    async def test_raises_403_when_notification_belongs_to_another_user(self, service, notification_repo_mock):
        owner_id = uuid4()
        other_user_id = uuid4()
        notification = make_notification(user_id=owner_id)
        notification_repo_mock.get_by_id.return_value = notification

        with pytest.raises(HTTPException) as exc:
            await service.mark_as_read(notification.id, current_user_id=other_user_id)

        assert exc.value.status_code == 403
        notification_repo_mock.mark_as_read.assert_not_awaited()
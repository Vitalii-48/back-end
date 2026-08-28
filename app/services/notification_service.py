# app/services/notification_service.py
import uuid
from typing import Sequence
from fastapi import HTTPException, status
from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository


class NotificationService:
    def __init__(self, notification_repository: NotificationRepository):
        self.notification_repository = notification_repository

    async def notify_company_about_new_quiz(
            self, member_ids: list[uuid.UUID], company_name: str, quiz_title: str) -> None:
        """
        Автоматично створює сповіщення для всіх учасників компанії при створенні квізу.
        Приймає готовий список user_ids, ім'я компанії та назву квізу.
        """
        # Звертаємося до user_id учасників, оскільки сповіщення прив'язані до користувачів

        if not member_ids:
            return

        message = f'Нова вікторина "{quiz_title}" доступна у компанії "{company_name}"'
        await self.notification_repository.create_bulk(member_ids, message)

    async def get_user_notifications(
            self, user_id: uuid.UUID, page: int = 1, per_page: int = 10) -> tuple[Sequence[Notification], int]:
        """
        Отримує список сповіщень користувача разом із їхньою загальною кількістю.
        Повністю сумісний зі схемою NotificationListResponse.
        """
        skip = (page - 1) * per_page
        return await self.notification_repository.get_user_notifications_with_count(
            user_id=user_id,
            skip=skip,
            limit=per_page)

    async def mark_as_read(self, notification_id: uuid.UUID, current_user_id: uuid.UUID) -> Notification:
        """
        Позначає сповіщення як прочитане із суворим дотриманням прав доступу.
        Спочатку перевіряє існування (404), потім — приналежність (403).
        """
        notification = await self.notification_repository.get_by_id(notification_id)

        # 1. Перевірка на існування (Захист від витоку інформації)
        if notification is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )

        # 2. Перевірка прав доступу
        if notification.user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not your notification"
            )

        return await self.notification_repository.mark_as_read(notification)
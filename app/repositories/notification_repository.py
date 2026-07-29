# app/repositories/notification_repository.py
from typing import Sequence
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.enums import NotificationStatus


class NotificationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_bulk(self, user_ids: list[UUID], message: str) -> None:
        """
        Ефективно створює сповіщення для багатьох користувачів одночасно.
        Запобігає проблемі N+1 запитів при масовій розсилці (тригер нового квізу).
        """
        notifications = [
            Notification(
                user_id=user_id,
                message=message,
                status=NotificationStatus.UNREAD
            )
            for user_id in user_ids
        ]
        self.session.add_all(notifications)
        await self.session.commit()

    async def create_many(self, notifications_data: list[dict]) -> None:
        """
        Ефективно створює сповіщення з РІЗНИМ текстом для кожного користувача.
        На відміну від create_bulk (один message для всіх), тут message
        індивідуальний — наприклад, для нагадувань про конкретний пропущений квіз.
        Запобігає N+1 запитів у фоновому scheduler-таску.
        """
        notifications = [
            Notification(
                user_id=item["user_id"],
                message=item["message"],
                status=NotificationStatus.UNREAD
            )
            for item in notifications_data
        ]
        self.session.add_all(notifications)
        await self.session.commit()

    async def get_user_notifications_with_count(
        self, user_id: UUID, skip: int = 0, limit: int = 10
    ) -> tuple[Sequence[Notification], int]:
        """
        Отримує всі сповіщення користувача та їхню загальну кількість
        для валідації через NotificationListResponse.
        """
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .order_by(Notification.created_at.desc())
        )
        result = await self.session.execute(stmt)
        notifications = result.scalars().all()

        count_stmt = select(func.count()).where(Notification.user_id == user_id)
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        return notifications, total

    async def get_by_id(self, notification_id: UUID) -> Notification | None:
        """Знаходить одне сповіщення за його ID."""
        result = await self.session.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        return result.scalar_one_or_none()

    async def mark_as_read(self, notification: Notification) -> Notification:
        """Переводить статус сповіщення в READ."""
        notification.status = NotificationStatus.READ
        await self.session.flush()
        return notification
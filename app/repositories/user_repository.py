import logging
from uuid import UUID
from datetime import datetime, UTC

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.user import User

logger = logging.getLogger(__name__)

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self, skip: int = 0, limit: int = 10) -> tuple[list[User], int]:
        # Отримуємо список юзерів з пагінацією
        result = await self.session.execute(
            select(User).offset(skip).limit(limit)
        )
        users = list(result.scalars().all())

        # Рахуємо загальну кількість
        total = await self.session.scalar(select(func.count(User.id)))
        logger.debug(f"Fetched {len(users)} users, total={total}")
        return users, total or 0

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update(self, user: User) -> User:
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        await self.session.delete(user)
        await self.session.commit()

    async def update_last_attempt(self, user_id: UUID) -> None:
        user = await self.get_by_id(user_id)
        if user:
            user.last_quiz_attempt = datetime.now(UTC)
            await self.session.commit()
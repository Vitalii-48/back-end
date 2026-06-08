import logging
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user_repository import UserRepository
from app.models.user import User
from app.schemas.user import SignUpRequest, UserUpdateRequest
from app.utils.hashing import hash_password

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    async def get_all_users(self, page: int, per_page: int) -> tuple[list[User], int]:
        skip = (page - 1) * per_page
        return await self.repo.get_all(skip=skip, limit=per_page)

    async def get_user_by_id(self, user_id: int) -> User:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id={user_id} not found"
            )
        return user

    async def create_user(self, data: SignUpRequest) -> User:
        # Перевіряємо чи email вже існує (conflict — конфлікт)
        existing = await self.repo.get_by_email(data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists"
            )
        user = User(
            username=data.username,
            email=data.email,
            hashed_password=hash_password(data.password),
        )
        logger.info(f"Creating user: {data.email}")
        return await self.repo.create(user)

    async def update_user(self, user_id: int, data: UserUpdateRequest) -> User:
        user = await self.get_user_by_id(user_id)

        if data.username is not None:
            user.username = data.username
        if data.password is not None:
            # Хешуємо новий пароль перед збереженням
            user.hashed_password = hash_password(data.password)

        logger.info(f"Updating user id={user_id}")
        return await self.repo.update(user)

    async def delete_user(self, user_id: int) -> None:
        user = await self.get_user_by_id(user_id)
        logger.info(f"Deleting user id={user_id}")
        await self.repo.delete(user)
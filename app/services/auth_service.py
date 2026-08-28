import bcrypt
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.config import settings
from app.repositories.user_repository import UserRepository
from app.schemas.auth import SignInRequest, TokenResponse
from app.core.security import create_access_token
from app.utils.auth0 import verify_auth0_token

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession):
        self.user_repo = UserRepository(session)

    async def sign_in(self, data: SignInRequest) -> TokenResponse:
        """
        Класичний вхід через email + пароль.
        Повертає JWT токен якщо дані вірні.
        """
        # Шукаємо користувача за email
        user = await self.user_repo.get_by_email(data.email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",  # Невірні дані
            )


        # Перевіряємо пароль
        password_valid = bcrypt.checkpw(
            data.password.encode("utf-8"),
            user.hashed_password.encode("utf-8")
        )

        if not password_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        logger.info(f"User {user.email} signed in successfully")

        # Створюємо токен. "sub" (subject — суб'єкт) — стандартна назва поля для ID
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
            }
        )
        return TokenResponse(access_token=access_token)

    async def auth0_sign_in(self, token: str) -> TokenResponse:
        """
        Вхід через Auth0 токен.
        Якщо користувача немає в БД — створюємо автоматично.
        """
        # Перевіряємо Auth0 токен і отримуємо дані
        payload = await verify_auth0_token(token)

        # Auth0 кладе email у payload як claim (заявка/твердження)
        email = (
                payload.get("email")
                or payload.get(f"https://{settings.AUTH0_DOMAIN}/email")
                or payload.get(f"{settings.AUTH0_DOMAIN}/email")
        )

        if not isinstance(email, str) or not email:            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not found in Auth0 token"
            )
        # Шукаємо або створюємо користувача
        user = await self.user_repo.get_by_email(str(email))

        if not user:
            logger.info(f"Creating new user from Auth0: {email}")
            # Імпортуємо тут щоб уникнути circular import (циклічного імпорту)
            from app.models.user import User
            from app.utils.hashing import hash_password
            import uuid
            user = await self.user_repo.create(
                User(
                    id=uuid.uuid4(),  # Явно генеруємо UUID тут!
                    email=email,
                    username=email.split("@")[0],  # Ім'я з email
                    hashed_password=hash_password(uuid.uuid4().hex),
                )
            )

        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
            }
        )
        return TokenResponse(access_token=access_token)
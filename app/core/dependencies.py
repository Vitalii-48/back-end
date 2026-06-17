import uuid

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db_postgres import get_db_postgres
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.services.company_service import CompanyService
from app.core.security import get_current_user_id


def get_auth_service(
    db: AsyncSession = Depends(get_db_postgres),
) -> AuthService:
    return AuthService(db)


def get_user_service(
    db: AsyncSession = Depends(get_db_postgres),
) -> UserService:
    return UserService(db)


async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service),
) -> User:
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )

    return await user_service.get_user_by_id(user_uuid)

async def get_company_service(
    session: AsyncSession = Depends(get_db_postgres),
) -> CompanyService:
    return CompanyService(session)
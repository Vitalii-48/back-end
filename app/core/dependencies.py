import uuid

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db_postgres import get_db_postgres
from app.models.user import User
from app.repositories.quiz_repository import QuizRepository
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.services.company_service import CompanyService
from app.services.company_member_service import CompanyMemberService, CompanyMemberRepository
from app.services.company_request_service import CompanyRequestService
from app.services.quiz_service import QuizService
from app.core.security import get_current_user_id


def get_auth_service(
    session: AsyncSession = Depends(get_db_postgres),
) -> AuthService:
    return AuthService(session)


def get_user_service(
    session: AsyncSession = Depends(get_db_postgres),
) -> UserService:
    return UserService(session)


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


async def get_company_member_service(
    session: AsyncSession = Depends(get_db_postgres),
) -> CompanyMemberService:
    return CompanyMemberService(session)


async def get_company_request_service(
    session: AsyncSession = Depends(get_db_postgres),
) -> CompanyRequestService:
    return CompanyRequestService(session)


# Функцію-залежність для квізів:
async def get_quiz_service(
        session: AsyncSession = Depends(get_db_postgres),
) -> QuizService:
    quiz_repo = QuizRepository(session)
    member_repo = CompanyMemberRepository(session)
    return QuizService(quiz_repo=quiz_repo, member_repo=member_repo)
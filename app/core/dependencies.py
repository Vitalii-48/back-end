import uuid

from fastapi import Depends, HTTPException,  Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_user_id
from app.database.db_postgres import get_db_postgres

from app.models.user import User
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.company_repository import CompanyRepository

from app.repositories.user_repository import UserRepository
from app.repositories.quiz_repository import QuizRepository
from app.repositories.quiz_result_repository import QuizResultRepository
from app.repositories.quiz_cache_repository import QuizCacheRepository
from app.services.analytics_service import AnalyticsService
from app.services.auth_service import AuthService
from app.services.notification_service import NotificationService
from app.services.quiz_import_service import QuizImportService

from app.services.user_service import UserService
from app.services.company_service import CompanyService
from app.services.company_member_service import CompanyMemberService
from app.repositories.company_member_repository import CompanyMemberRepository
from app.services.company_request_service import CompanyRequestService
from app.services.quiz_result_service import QuizWorkflowService
from app.services.quiz_service import QuizService

from redis.asyncio import Redis

from app.services.export_service import ExportService



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


def get_redis(request: Request):
    return request.app.state.redis


async def get_quiz_service(
        session: AsyncSession = Depends(get_db_postgres),
) -> QuizService:
    return QuizService(
        quiz_repo=QuizRepository(session),
        member_repo=CompanyMemberRepository(session),
        company_repo=CompanyRepository(session),
        notification_service=NotificationService(
            NotificationRepository(session)
        ),
    )


async def get_quiz_result_service(
    session: AsyncSession = Depends(get_db_postgres),
    redis=Depends(get_redis),
) -> QuizWorkflowService:
    return QuizWorkflowService(
        quiz_repo=QuizRepository(session),
        quiz_result_repo=QuizResultRepository(session),
        member_repo=CompanyMemberRepository(session),
        user_repo=UserRepository(session),
        quiz_cache_repo=QuizCacheRepository(redis),
    )


def get_company_repository(db: AsyncSession = Depends(get_db_postgres)) -> CompanyRepository:
    return CompanyRepository(db)


def get_membership_repository(db: AsyncSession = Depends(get_db_postgres)) -> CompanyMemberRepository:
    return CompanyMemberRepository(db)


def get_redis_repository(redis: Redis = Depends(get_redis)) -> QuizCacheRepository:
    return QuizCacheRepository(redis)


def get_export_service(
        redis_repository: QuizCacheRepository = Depends(get_redis_repository),
        company_repository: CompanyRepository = Depends(get_company_repository),
    membership_repository: CompanyMemberRepository = Depends(get_membership_repository),
) -> ExportService:
    return ExportService(
        redis_repository=redis_repository,
        company_repository=company_repository,
        membership_repository=membership_repository,
    )


async def get_analytics_service(
    session: AsyncSession = Depends(get_db_postgres),
) -> AnalyticsService:
    return AnalyticsService(
        analytics_repository=AnalyticsRepository(session),
        company_repository=CompanyRepository(session),
        quiz_repository=QuizRepository(session),
    )


async def get_notification_service(
        session: AsyncSession = Depends(get_db_postgres)
) -> NotificationService:
    repository = NotificationRepository(session)
    return NotificationService(repository)


async def get_quiz_import_service(
    session: AsyncSession = Depends(get_db_postgres),
) -> QuizImportService:
    return QuizImportService(
        quiz_repo=QuizRepository(session),
        member_repo=CompanyMemberRepository(session),
        company_repo=CompanyRepository(session),
    )
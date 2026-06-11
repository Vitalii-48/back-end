from fastapi import APIRouter, Depends, status
from app.models.user import User
from app.schemas.user import SignUpRequest, UserDetailResponse
from app.schemas.auth import SignInRequest, Auth0TokenRequest, TokenResponse
from app.services.auth_service import AuthService  # Імпортуй свій AuthService
from app.services.user_service import UserService
from app.core.dependencies import get_auth_service, get_user_service, get_current_user # Твоя функція (або функція з іншого файлу) для ін'єкції сервісу

router = APIRouter(prefix="/auth", tags=["Auth"])

me_router = APIRouter(tags=["Auth"])

@router.post(
    "/signup",
    response_model=UserDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Реєстрація нового користувача",
    description="Приймає обов'язкові поля username, email (з валідацією формату) та password (мінімум 8 символів)."
)
async def signup(
        payload: SignUpRequest,
        user_service: UserService = Depends(get_user_service),
):
    return await user_service.create_user(payload)


@router.post(
    "/signin",
    status_code=status.HTTP_200_OK,
    summary="Авторизація користувача (Вхід)",
    description="Перевіряє правильність емейлу та паролю для входу в систему."
)
async def signin(payload: SignInRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    return await auth_service.sign_in(payload)

@router.post(
    "/auth0",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with Auth0 token",
)
async def auth0_signin(
    payload: Auth0TokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.auth0_sign_in(payload.token)


# ендпоінт /me
@me_router.get(
    "/me",
    response_model=UserDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user
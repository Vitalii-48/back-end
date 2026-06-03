from fastapi import APIRouter, status
from app.schemas.user import SignUpRequest, SignInRequest

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)


@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
    summary="Реєстрація нового користувача",
    description="Приймає обов'язкові поля username, email (з валідацією формату) та password (мінімум 8 символів)."
)
def signup(payload: SignUpRequest):
    return {
        "message": "User registered successfully (mock)",
        "user_data": {
            "username": payload.username,
            "email": payload.email
        }
    }


@router.post(
    "/signin",
    status_code=status.HTTP_200_OK,
    summary="Авторизація користувача (Вхід)",
    description="Перевіряє правильність емейлу та паролю для входу в систему."
)
def signin(payload: SignInRequest):
    return {
        "message": "User logged in successfully (mock)",
        "email": payload.email
    }
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
    username: str = Field(..., description="Унікальне ім'я користувача", examples=["User"])
    email: EmailStr = Field(..., description="Електронна пошта", examples=["user@example.com"])

class SignUpRequest(UserBase):
    password: str = Field(..., min_length=8, examples=["secret_password"])

class UserCreate(SignUpRequest):
    """Схема для внутрішнього створення користувача в репозиторії"""
    pass

# Email змінювати заборонено — він є ідентифікатором (identifier) у системі та Auth0.
class UserUpdateRequest(BaseModel):
    username: str | None = Field(
        default=None,
        description="Нове ім'я користувача (username). Email змінити не можна.",
        examples=["new_user"])
    password: str | None = Field(
        default=None,
        min_length=8,
        description="Новий пароль (password). Мінімум 8 символів.",
        examples=["new_secret_password"])

class UserDetailResponse(UserBase):
    id: UUID = Field(..., examples=["8c5c32b7-8b4f-4f3b-9f41-02464724b4c2"])
    is_active: bool = Field(..., examples=[True])
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class UsersListResponse(BaseModel):
    users: list[UserDetailResponse]
    total: int = Field(..., description="Загальна кількість користувачів у базі", examples=[15])

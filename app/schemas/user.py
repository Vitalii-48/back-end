from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
    username: str = Field(..., description="Унікальне ім'я користувача", examples=["User"])
    email: EmailStr = Field(..., description="Електронна пошта", examples=["user@example.com"])
class SignInRequest(BaseModel):
    email: EmailStr = Field(..., examples=["user@example.com"])
    password: str = Field(..., examples=["secret_password"])

class SignUpRequest(UserBase):
    password: str = Field(..., min_length=8, examples=["secret_password"])

class UserUpdateRequest(BaseModel):
    username: str | None = Field(default=None, examples=["new_user"])
    password: str | None = Field(default=None, min_length=8, examples=["new_secret_password"])

class UserDetailResponse(UserBase):
    id: int = Field(..., examples=[1])
    is_active: bool = Field(..., examples=[True])
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class UsersListResponse(BaseModel):
    users: list[UserDetailResponse]
    total: int = Field(..., description="Загальна кількість користувачів у базі", examples=[15])
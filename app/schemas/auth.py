from pydantic import BaseModel, EmailStr, Field

class SignInRequest(BaseModel):
    """Схема для входу через логін/пароль"""
    email: EmailStr = Field(..., examples=["user@example.com"])
    password: str = Field(..., examples=["secret_password"])


class TokenResponse(BaseModel):
    """Відповідь з токеном після успішного входу"""
    access_token: str = Field(..., description="JWT access токен для доступу до API")
    token_type: str = Field(default="bearer", description="Тип токена")


class Auth0TokenRequest(BaseModel):
    """Токен від Auth0, який приходить з фронтенду"""
    token: str = Field(..., description="Токен, отриманий від Auth0")
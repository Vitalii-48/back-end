import jwt
from fastapi import HTTPException, status
from app.core.config import settings

# Створюємо клієнт для автоматичного завантаження та КЕШУВАННЯ публічних ключів Auth0
jwks_url = f"https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json"
jwks_client = jwt.PyJWKClient(jwks_url)


async def verify_auth0_token(token: str) -> dict:
    """
    Перевіряє Auth0 токен і повертає його payload (корисні дані).
    """
    try:
        # PyJWKClient сам парсить невалідований заголовок, знаходить 'kid'
        # і витягує потрібний публічний ключ із JWKS
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # Декодуємо та валідуємо токен
        payload = jwt.decode(
            token,
            signing_key.key,  # Передаємо об'єкт ключа, який зрозуміє PyJWT
            algorithms=[settings.AUTH0_ALGORITHMS],
            audience=settings.AUTH0_API_AUDIENCE,
            issuer=f"https://{settings.AUTH0_DOMAIN}/",
        )
        return payload

    except jwt.exceptions.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Auth0 token has expired"
        )
    except jwt.exceptions.InvalidAudienceError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token audience"
        )
    except Exception as e:
        # Ловимо всі інші помилки валідації PyJWT (InvalidTokenError тощо)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Auth0 token: {str(e)}"
        )
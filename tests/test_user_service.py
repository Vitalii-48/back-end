import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from fastapi import HTTPException

from app.services.user_service import UserService
from app.schemas.user import UserUpdateRequest, SignUpRequest


# ─── Helpers (допоміжні функції) ────────────────────────────────────────────

def make_user(user_id: UUID = None, email: str = "test@example.com") -> MagicMock:
    """
    Створює фейкового (fake) користувача — MagicMock з потрібними полями.
    MagicMock — це об'єкт який імітує (imitate) реальний об'єкт User,
    але не звертається до бази даних (database).
    """
    user = MagicMock()
    user.id = user_id or uuid4()
    user.email = email
    user.username = "testuser"
    user.hashed_password = "hashed_old_password"
    return user


def make_service() -> tuple[UserService, MagicMock]:
    """
    Створює UserService з підробленим (mocked) репозиторієм (repository).
    Повертає кортеж (tuple): (service, mock_repo).
    """
    mock_db = AsyncMock()
    service = UserService(mock_db)
    # Підміняємо реальний репозиторій на AsyncMock —
    # щоб не звертатись до реальної бази даних під час тестів
    service.repo = AsyncMock()
    return service, service.repo


# ─── Tests: update_user ──────────────────────────────────────────────────────

class TestUpdateUser:

    @pytest.mark.asyncio
    async def test_update_own_profile_success(self):
        """
        ✅ Користувач оновлює СВІЙ профіль — має спрацювати успішно (success).
        current_user.id == user_id → дозволено (allowed).
        """
        user_id = uuid4()
        current_user = make_user(user_id=user_id)
        existing_user = make_user(user_id=user_id)

        service, mock_repo = make_service()
        # get_by_id повертає existing_user
        mock_repo.get_by_id.return_value = existing_user
        # update повертає той самий об'єкт
        mock_repo.update.return_value = existing_user

        data = UserUpdateRequest(username="new_name")
        result = await service.update_user(user_id, data, current_user)

        # Перевіряємо що update був викликаний (called) рівно один раз
        mock_repo.update.assert_called_once()
        assert result == existing_user

    @pytest.mark.asyncio
    async def test_update_other_profile_forbidden(self):
        """
        ❌ Користувач намагається оновити ЧУЖИЙ профіль.
        current_user.id != user_id → 403 Forbidden.
        """
        current_user = make_user(user_id=uuid4())
        other_user_id = uuid4()  # інший ID — не збігається з current_user.id

        service, mock_repo = make_service()

        data = UserUpdateRequest(username="hacker_name")

        # Очікуємо що буде підняте виключення (exception) HTTPException зі статусом 403
        with pytest.raises(HTTPException) as exc_info:
            await service.update_user(other_user_id, data, current_user)

        assert exc_info.value.status_code == 403
        # Репозиторій взагалі не має викликатись — перевірка відбувається ДО звернення до БД
        mock_repo.get_by_id.assert_not_called()
        mock_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_password_is_hashed(self):
        """
        ✅ При оновленні пароль має зберігатись у хешованому (hashed) вигляді,
        а не як plain text (відкритий текст).
        """
        user_id = uuid4()
        current_user = make_user(user_id=user_id)
        existing_user = make_user(user_id=user_id)

        service, mock_repo = make_service()
        mock_repo.get_by_id.return_value = existing_user
        mock_repo.update.return_value = existing_user

        data = UserUpdateRequest(password="new_password_123")
        await service.update_user(user_id, data, current_user)

        # Переконуємось що hashed_password не дорівнює plain text паролю
        assert existing_user.hashed_password != "new_password_123"

    @pytest.mark.asyncio
    async def test_update_email_field_is_not_in_schema(self):
        """
        ✅ Перевіряємо що UserUpdateRequest не містить поля email.
        Якби хтось передав email — Pydantic просто проігнорує його
        (завдяки відсутності поля в схемі).
        """
        # model_fields — словник (dict) всіх полів схеми
        fields = UserUpdateRequest.model_fields
        assert "email" not in fields, (
            "Email не повинен бути в UserUpdateRequest! "
            "Користувач не може змінювати свій email."
        )

    @pytest.mark.asyncio
    async def test_update_user_not_found(self):
        """
        ❌ Якщо user_id не існує в базі — має повернути 404 Not Found.
        Перевірка відбувається після permission check (перевірки прав).
        """
        user_id = uuid4()
        current_user = make_user(user_id=user_id)  # ID збігається — має пройти permission check

        service, mock_repo = make_service()
        # Повертаємо None — користувача не знайдено (not found)
        mock_repo.get_by_id.return_value = None

        data = UserUpdateRequest(username="some_name")

        with pytest.raises(HTTPException) as exc_info:
            await service.update_user(user_id, data, current_user)

        assert exc_info.value.status_code == 404


# ─── Tests: delete_user ──────────────────────────────────────────────────────

class TestDeleteUser:

    @pytest.mark.asyncio
    async def test_delete_own_profile_success(self):
        """
        ✅ Користувач видаляє СВІЙ профіль — має спрацювати успішно.
        """
        user_id = uuid4()
        current_user = make_user(user_id=user_id)
        existing_user = make_user(user_id=user_id)

        service, mock_repo = make_service()
        mock_repo.get_by_id.return_value = existing_user

        await service.delete_user(user_id, current_user)

        # Переконуємось що delete був викликаний рівно один раз
        mock_repo.delete.assert_called_once_with(existing_user)

    @pytest.mark.asyncio
    async def test_delete_other_profile_forbidden(self):
        """
        ❌ Користувач намагається видалити ЧУЖИЙ профіль — 403 Forbidden.
        """
        current_user = make_user(user_id=uuid4())
        other_user_id = uuid4()

        service, mock_repo = make_service()

        with pytest.raises(HTTPException) as exc_info:
            await service.delete_user(other_user_id, current_user)

        assert exc_info.value.status_code == 403
        # delete не має бути викликаний взагалі
        mock_repo.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self):
        """
        ❌ Спроба видалити неіснуючого користувача — 404 Not Found.
        ID збігається (permission пройдено), але в БД такого користувача немає.
        """
        user_id = uuid4()
        current_user = make_user(user_id=user_id)

        service, mock_repo = make_service()
        mock_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await service.delete_user(user_id, current_user)

        assert exc_info.value.status_code == 404
        mock_repo.delete.assert_not_called()
# tests/services/test_export_service.py

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException

from app.services.export_service import ExportService
from app.models.enums import CompanyRole


@pytest.fixture
def export_service():
    """
    Fixture (фікстура — "готовий об'єкт для повторного використання в тестах").
    Створює ExportService з mock-репозиторіями замість реальних.
    """
    redis_repository = AsyncMock()
    company_repository = AsyncMock()
    membership_repository = AsyncMock()

    service = ExportService(
        redis_repository=redis_repository,
        company_repository=company_repository,
        membership_repository=membership_repository,
    )
    return service


class TestExportMyResults:
    """Тести для методу export_my_results (особисті результати користувача)."""

    @pytest.mark.asyncio
    async def test_returns_json_when_format_is_json(self, export_service):
        requester_id = uuid.uuid4()
        fake_data = [{"user_id": str(requester_id), "answers": []}]
        export_service.redis_repository.get_attempts_by_pattern.return_value = fake_data

        result = await export_service.export_my_results(
            requester_id=requester_id,
            company_id=None,
            quiz_id=None,
            export_format="json",
        )

        assert result == fake_data

    @pytest.mark.asyncio
    async def test_returns_csv_when_format_is_csv(self, export_service):
        requester_id = uuid.uuid4()
        fake_data = [
            {
                "user_id": str(requester_id),
                "company_id": "c1",
                "quiz_id": "q1",
                "completed_at": "2026-07-01",
                "answers": [
                    {"question_id": "q1", "selected_option_ids": ["opt1"], "is_correct": True}
                ],
            }
        ]
        export_service.redis_repository.get_attempts_by_pattern.return_value = fake_data

        result = await export_service.export_my_results(
            requester_id=requester_id,
            company_id=None,
            quiz_id=None,
            export_format="csv",
        )

        csv_content = result.getvalue()
        assert "user_id,company_id,quiz_id" in csv_content
        assert "opt1" in csv_content

    @pytest.mark.asyncio
    async def test_builds_pattern_with_requester_id(self, export_service):
        """Перевіряємо, що pattern будується саме з requester_id, а не з чужим ID."""
        requester_id = uuid.uuid4()
        export_service.redis_repository.get_attempts_by_pattern.return_value = []

        await export_service.export_my_results(
            requester_id=requester_id,
            company_id=None,
            quiz_id=None,
            export_format="json",
        )

        called_pattern = export_service.redis_repository.get_attempts_by_pattern.call_args[0][0]
        assert str(requester_id) in called_pattern


class TestExportCompanyQuizResults:
    """Тести для методу export_company_quiz_results (результати компанії)."""

    @pytest.mark.asyncio
    async def test_raises_404_if_company_not_found(self, export_service):
        export_service.company_repository.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await export_service.export_company_quiz_results(
                company_id=uuid.uuid4(),
                requester_id=uuid.uuid4(),
                target_user_id=None,
                quiz_id=None,
                export_format="json",
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Company not found"

    @pytest.mark.asyncio
    async def test_raises_404_if_target_user_not_a_member(self, export_service):
        export_service.company_repository.get_by_id.return_value = MagicMock()
        export_service.membership_repository.get_member.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await export_service.export_company_quiz_results(
                company_id=uuid.uuid4(),
                requester_id=uuid.uuid4(),
                target_user_id=uuid.uuid4(),
                quiz_id=None,
                export_format="json",
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "User is not a member of this company"

    @pytest.mark.asyncio
    async def test_raises_403_if_requester_has_no_membership(self, export_service):
        export_service.company_repository.get_by_id.return_value = MagicMock()
        # target_user_id не переданий, тому другу перевірку пропускаємо,
        # одразу переходимо до перевірки requester_mem
        export_service.membership_repository.get_member.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await export_service.export_company_quiz_results(
                company_id=uuid.uuid4(),
                requester_id=uuid.uuid4(),
                target_user_id=None,
                quiz_id=None,
                export_format="json",
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_raises_403_if_requester_role_is_member(self, export_service):
        fake_member = MagicMock()
        fake_member.role = CompanyRole.MEMBER

        export_service.company_repository.get_by_id.return_value = MagicMock()
        export_service.membership_repository.get_member.return_value = fake_member

        with pytest.raises(HTTPException) as exc_info:
            await export_service.export_company_quiz_results(
                company_id=uuid.uuid4(),
                requester_id=uuid.uuid4(),
                target_user_id=None,
                quiz_id=None,
                export_format="json",
            )

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Not enough permissions"

    @pytest.mark.asyncio
    async def test_owner_can_export_company_results(self, export_service):
        owner_member = MagicMock()
        owner_member.role = CompanyRole.OWNER
        fake_data = [{"user_id": "u1", "answers": []}]

        export_service.company_repository.get_by_id.return_value = MagicMock()
        export_service.membership_repository.get_member.return_value = owner_member
        export_service.redis_repository.get_attempts_by_pattern.return_value = fake_data

        result = await export_service.export_company_quiz_results(
            company_id=uuid.uuid4(),
            requester_id=uuid.uuid4(),
            target_user_id=None,
            quiz_id=None,
            export_format="json",
        )

        assert result == fake_data

    @pytest.mark.asyncio
    async def test_admin_can_export_company_results(self, export_service):
        """Перевіряємо, що ADMIN, а не тільки OWNER, теж має доступ."""
        admin_member = MagicMock()
        admin_member.role = CompanyRole.ADMIN

        export_service.company_repository.get_by_id.return_value = MagicMock()
        export_service.membership_repository.get_member.return_value = admin_member
        export_service.redis_repository.get_attempts_by_pattern.return_value = []

        result = await export_service.export_company_quiz_results(
            company_id=uuid.uuid4(),
            requester_id=uuid.uuid4(),
            target_user_id=None,
            quiz_id=None,
            export_format="json",
        )

        assert result == []


class TestBuildPattern:
    """Тести для статичного методу _build_pattern."""

    def test_pattern_with_all_filters(self):
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        quiz_id = uuid.uuid4()

        pattern = ExportService._build_pattern(
            user_id=user_id, company_id=company_id, quiz_id=quiz_id
        )

        expected = f"quiz_attempt:{user_id}:{company_id}:{quiz_id}:*"
        assert pattern == expected

    def test_pattern_with_no_filters_uses_wildcards(self):
        pattern = ExportService._build_pattern()

        assert pattern == "quiz_attempt:*:*:*:*"


class TestToCsv:
    """Тести для статичного методу _to_csv."""

    def test_csv_contains_header_row(self):
        result = ExportService._to_csv([])
        content = result.getvalue()

        assert "user_id,company_id,quiz_id,completed_at,question_id,selected_option_ids,is_correct" in content

    def test_csv_flattens_multiple_answers(self):
        """
        Перевіряємо, що одна attempt (спроба) з кількома answers (відповідями)
        перетворюється на КІЛЬКА рядків CSV — по одному на кожну відповідь.
        """
        data = [
            {
                "user_id": "u1",
                "company_id": "c1",
                "quiz_id": "q1",
                "completed_at": "2026-07-01",
                "answers": [
                    {"question_id": "q1", "selected_option_ids": ["opt1"], "is_correct": True},
                    {"question_id": "q2", "selected_option_ids": ["opt2", "opt3"], "is_correct": False},
                ],
            }
        ]

        result = ExportService._to_csv(data)
        content = result.getvalue()
        rows = content.strip().split("\n")

        # 1 рядок заголовку + 2 рядки з answers = 3 рядки всього
        assert len(rows) == 3
        assert "opt2,opt3" in content
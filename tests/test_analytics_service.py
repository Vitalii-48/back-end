# tests/test_analytics_service.py

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.enums import CompanyRole
from app.services.analytics_service import AnalyticsService, _safe_percentage
from app.models.user import User

# ---------- Fixtures (спільні для всіх тестів) ----------

@pytest.fixture
def analytics_repo_mock():
    return AsyncMock()


@pytest.fixture
def company_repo_mock():
    return AsyncMock()


@pytest.fixture
def quiz_repo_mock():
    return AsyncMock()


@pytest.fixture
def service(analytics_repo_mock, company_repo_mock, quiz_repo_mock):
    return AnalyticsService(
        analytics_repository=analytics_repo_mock,
        company_repository=company_repo_mock,
        quiz_repository=quiz_repo_mock,
    )


# ---------- Допоміжні функції для створення тестових даних ----------

def make_user(user_id):
    user = MagicMock(spec=User)
    user.id = user_id
    return user


def make_member(user_id, role=CompanyRole.MEMBER):
    return SimpleNamespace(user_id=user_id, role=role)


def make_company(owner_id, members=None):
    return SimpleNamespace(owner_id=owner_id, members=members or [])


def make_row(**kwargs):
    """Імітує SQLAlchemy Row — 'сирий' рядок результату SQL-запиту."""
    return SimpleNamespace(**kwargs)


def make_quiz(quiz_id, title):
    return SimpleNamespace(id=quiz_id, title=title)


# ============================================================
# _safe_percentage — тест допоміжної функції (helper), окремо
# ============================================================

class TestSafePercentage:
    def test_returns_correct_percentage(self):
        assert _safe_percentage(9, 10) == 90.0

    def test_returns_zero_when_total_is_zero(self):
        assert _safe_percentage(0, 0) == 0.0

    def test_returns_zero_when_correct_is_zero(self):
        assert _safe_percentage(0, 10) == 0.0

    def test_returns_hundred_when_all_correct(self):
        assert _safe_percentage(10, 10) == 100.0

    def test_rounds_to_two_decimals(self):
        assert _safe_percentage(1, 3) == 33.33


# ============================================================
# get_user_rating
# ============================================================

class TestGetUserRating:
    async def test_returns_correct_percentage(self, service, analytics_repo_mock):
        user_id = uuid4()
        analytics_repo_mock.get_user_overall_totals.return_value = make_row(
            total_correct=9, total_questions=10
        )

        result = await service.get_user_rating(user_id)

        assert result.overall_average == 90.0
        analytics_repo_mock.get_user_overall_totals.assert_awaited_once_with(user_id)

    async def test_returns_zero_when_no_results(self, service, analytics_repo_mock):
        analytics_repo_mock.get_user_overall_totals.return_value = make_row(
            total_correct=0, total_questions=0
        )

        result = await service.get_user_rating(uuid4())

        assert result.overall_average == 0.0

    async def test_calls_repository_exactly_once(self, service, analytics_repo_mock):
        analytics_repo_mock.get_user_overall_totals.return_value = make_row(
            total_correct=5, total_questions=5
        )

        await service.get_user_rating(uuid4())

        analytics_repo_mock.get_user_overall_totals.assert_awaited_once()


# ============================================================
# get_user_quiz_averages
# ============================================================

class TestGetUserQuizAverages:
    async def test_raises_404_when_quiz_not_found(self, service, quiz_repo_mock):
        quiz_repo_mock.get_quiz_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            await service.get_user_quiz_averages(uuid4(), uuid4())

        assert exc.value.status_code == 404

    async def test_does_not_call_analytics_repo_when_quiz_not_found(
        self, service, quiz_repo_mock, analytics_repo_mock
    ):
        """Перевіряємо, що при 404 сервіс НЕ робить зайвий SQL-запит."""
        quiz_repo_mock.get_quiz_by_id.return_value = None

        with pytest.raises(HTTPException):
            await service.get_user_quiz_averages(uuid4(), uuid4())

        analytics_repo_mock.get_user_quiz_weekly_totals.assert_not_awaited()

    async def test_groups_by_week_correctly(
        self, service, quiz_repo_mock, analytics_repo_mock
    ):
        quiz_id = uuid4()
        quiz_repo_mock.get_quiz_by_id.return_value = make_quiz(quiz_id, "Python Basics")
        analytics_repo_mock.get_user_quiz_weekly_totals.return_value = [
            make_row(week_start=datetime(2026, 6, 1), total_correct=8, total_questions=10),
            make_row(week_start=datetime(2026, 6, 8), total_correct=5, total_questions=10),
        ]

        result = await service.get_user_quiz_averages(uuid4(), quiz_id)

        assert result.quiz_title == "Python Basics"
        assert len(result.weekly_scores) == 2
        assert result.weekly_scores[0].average_score == 80.0
        assert result.weekly_scores[1].average_score == 50.0

    async def test_returns_empty_weekly_scores_when_no_attempts(
        self, service, quiz_repo_mock, analytics_repo_mock
    ):
        quiz_id = uuid4()
        quiz_repo_mock.get_quiz_by_id.return_value = make_quiz(quiz_id, "Empty Quiz")
        analytics_repo_mock.get_user_quiz_weekly_totals.return_value = []

        result = await service.get_user_quiz_averages(uuid4(), quiz_id)

        assert result.weekly_scores == []
        assert result.quiz_title == "Empty Quiz"


# ============================================================
# get_user_last_attempts
# ============================================================

class TestGetUserLastAttempts:
    async def test_returns_empty_list_when_no_attempts(self, service, analytics_repo_mock):
        analytics_repo_mock.get_user_last_attempts.return_value = []

        result = await service.get_user_last_attempts(uuid4())

        assert result == []

    async def test_batches_quiz_lookup_into_single_call(
        self, service, analytics_repo_mock, quiz_repo_mock
    ):
        """Перевіряємо N+1-оптимізацію: get_by_ids викликається ОДИН раз."""
        quiz_id_1, quiz_id_2 = uuid4(), uuid4()
        analytics_repo_mock.get_user_last_attempts.return_value = [
            make_row(quiz_id=quiz_id_1, last_completed_at=datetime(2026, 7, 1)),
            make_row(quiz_id=quiz_id_2, last_completed_at=datetime(2026, 7, 5)),
        ]
        quiz_repo_mock.get_by_ids.return_value = [
            make_quiz(quiz_id_1, "Quiz A"),
            make_quiz(quiz_id_2, "Quiz B"),
        ]

        result = await service.get_user_last_attempts(uuid4())

        assert len(result) == 2
        assert result[0].quiz_title == "Quiz A"
        assert result[1].quiz_title == "Quiz B"
        quiz_repo_mock.get_by_ids.assert_awaited_once()

    async def test_does_not_call_get_by_ids_when_no_attempts(
        self, service, analytics_repo_mock, quiz_repo_mock
    ):
        analytics_repo_mock.get_user_last_attempts.return_value = []

        await service.get_user_last_attempts(uuid4())

        quiz_repo_mock.get_by_ids.assert_not_awaited()

    async def test_falls_back_to_unknown_title_if_quiz_missing(
        self, service, analytics_repo_mock, quiz_repo_mock
    ):
        """Якщо квіз видалили, а результат лишився — назва має бути 'Unknown', без падіння."""
        quiz_id = uuid4()
        analytics_repo_mock.get_user_last_attempts.return_value = [
            make_row(quiz_id=quiz_id, last_completed_at=datetime(2026, 7, 1)),
        ]
        quiz_repo_mock.get_by_ids.return_value = []  # квіз не знайдено

        result = await service.get_user_last_attempts(uuid4())

        assert result[0].quiz_title == "Unknown"


# ============================================================
# get_company_members_averages
# ============================================================

class TestGetCompanyMembersAverages:
    async def test_raises_404_if_company_not_found(self, service, company_repo_mock):
        company_repo_mock.get_company_with_members.return_value = None

        with pytest.raises(HTTPException) as exc:
            await service.get_company_members_averages(uuid4(), make_user(uuid4()))

        assert exc.value.status_code == 404

    async def test_raises_403_for_regular_member(self, service, company_repo_mock):
        owner_id = uuid4()
        stranger_id = uuid4()
        company = make_company(owner_id, members=[make_member(stranger_id, CompanyRole.MEMBER)])
        company_repo_mock.get_company_with_members.return_value = company

        with pytest.raises(HTTPException) as exc:
            await service.get_company_members_averages(uuid4(), make_user(stranger_id))

        assert exc.value.status_code == 403

    async def test_allows_owner(self, service, company_repo_mock, analytics_repo_mock):
        owner_id = uuid4()
        member_id = uuid4()
        company_repo_mock.get_company_with_members.return_value = make_company(owner_id)
        analytics_repo_mock.get_company_members_weekly_totals.return_value = [
            make_row(user_id=member_id, week_start=datetime(2026, 6, 1), total_correct=7, total_questions=10),
        ]

        result = await service.get_company_members_averages(uuid4(), make_user(owner_id))

        assert len(result) == 1
        assert result[0].user_id == member_id
        assert result[0].weekly_scores[0].average_score == 70.0

    async def test_allows_admin(self, service, company_repo_mock, analytics_repo_mock):
        owner_id = uuid4()
        admin_id = uuid4()
        company = make_company(owner_id, members=[make_member(admin_id, CompanyRole.ADMIN)])
        company_repo_mock.get_company_with_members.return_value = company
        analytics_repo_mock.get_company_members_weekly_totals.return_value = []

        result = await service.get_company_members_averages(uuid4(), make_user(admin_id))

        assert result == []

    async def test_groups_multiple_members_separately(
        self, service, company_repo_mock, analytics_repo_mock
    ):
        """Перевіряємо, що дані ДВОХ різних учасників не змішуються між собою."""
        owner_id = uuid4()
        member_a, member_b = uuid4(), uuid4()
        company_repo_mock.get_company_with_members.return_value = make_company(owner_id)
        analytics_repo_mock.get_company_members_weekly_totals.return_value = [
            make_row(user_id=member_a, week_start=datetime(2026, 6, 1), total_correct=5, total_questions=10),
            make_row(user_id=member_b, week_start=datetime(2026, 6, 1), total_correct=8, total_questions=10),
        ]

        result = await service.get_company_members_averages(uuid4(), make_user(owner_id))

        result_by_user = {r.user_id: r for r in result}
        assert len(result) == 2
        assert result_by_user[member_a].weekly_scores[0].average_score == 50.0
        assert result_by_user[member_b].weekly_scores[0].average_score == 80.0


# ============================================================
# get_member_quiz_averages
# ============================================================

class TestGetMemberQuizAverages:
    async def test_raises_404_if_company_not_found(self, service, company_repo_mock):
        company_repo_mock.get_company_with_members.return_value = None

        with pytest.raises(HTTPException) as exc:
            await service.get_member_quiz_averages(uuid4(), uuid4(), make_user(uuid4()))

        assert exc.value.status_code == 404

    async def test_raises_403_for_regular_member(self, service, company_repo_mock):
        owner_id = uuid4()
        stranger_id = uuid4()
        company = make_company(owner_id, members=[make_member(stranger_id, CompanyRole.MEMBER)])
        company_repo_mock.get_company_with_members.return_value = company

        with pytest.raises(HTTPException) as exc:
            await service.get_member_quiz_averages(uuid4(), uuid4(), make_user(stranger_id))

        assert exc.value.status_code == 403

    async def test_groups_by_quiz_for_target_user(
        self, service, company_repo_mock, analytics_repo_mock, quiz_repo_mock
    ):
        owner_id = uuid4()
        target_user_id = uuid4()
        quiz_id = uuid4()
        company_repo_mock.get_company_with_members.return_value = make_company(owner_id)
        analytics_repo_mock.get_member_quiz_weekly_totals.return_value = [
            make_row(quiz_id=quiz_id, week_start=datetime(2026, 6, 1), total_correct=6, total_questions=10),
        ]
        quiz_repo_mock.get_by_ids.return_value = [make_quiz(quiz_id, "SQL Advanced")]

        result = await service.get_member_quiz_averages(uuid4(), target_user_id, make_user(owner_id))

        assert len(result) == 1
        assert result[0].quiz_title == "SQL Advanced"
        assert result[0].weekly_scores[0].average_score == 60.0

    async def test_returns_empty_list_when_no_attempts(
        self, service, company_repo_mock, analytics_repo_mock
    ):
        owner_id = uuid4()
        company_repo_mock.get_company_with_members.return_value = make_company(owner_id)
        analytics_repo_mock.get_member_quiz_weekly_totals.return_value = []

        result = await service.get_member_quiz_averages(uuid4(), uuid4(), make_user(owner_id))

        assert result == []

    async def test_batches_quiz_lookup_into_single_call(
        self, service, company_repo_mock, analytics_repo_mock, quiz_repo_mock
    ):
        owner_id = uuid4()
        quiz_id_1, quiz_id_2 = uuid4(), uuid4()
        company_repo_mock.get_company_with_members.return_value = make_company(owner_id)
        analytics_repo_mock.get_member_quiz_weekly_totals.return_value = [
            make_row(quiz_id=quiz_id_1, week_start=datetime(2026, 6, 1), total_correct=5, total_questions=10),
            make_row(quiz_id=quiz_id_2, week_start=datetime(2026, 6, 1), total_correct=9, total_questions=10),
        ]
        quiz_repo_mock.get_by_ids.return_value = [
            make_quiz(quiz_id_1, "Quiz A"),
            make_quiz(quiz_id_2, "Quiz B"),
        ]

        await service.get_member_quiz_averages(uuid4(), uuid4(), make_user(owner_id))

        quiz_repo_mock.get_by_ids.assert_awaited_once()


# ============================================================
# get_company_last_attempts
# ============================================================

class TestGetCompanyLastAttempts:
    async def test_raises_404_if_company_not_found(self, service, company_repo_mock):
        company_repo_mock.get_company_with_members.return_value = None

        with pytest.raises(HTTPException) as exc:
            await service.get_company_last_attempts(uuid4(), make_user(uuid4()))

        assert exc.value.status_code == 404

    async def test_raises_403_for_regular_member(self, service, company_repo_mock):
        owner_id = uuid4()
        stranger_id = uuid4()
        company = make_company(owner_id, members=[make_member(stranger_id, CompanyRole.MEMBER)])
        company_repo_mock.get_company_with_members.return_value = company

        with pytest.raises(HTTPException) as exc:
            await service.get_company_last_attempts(uuid4(), make_user(stranger_id))

        assert exc.value.status_code == 403

    async def test_allows_admin_and_returns_correct_data(
        self, service, company_repo_mock, analytics_repo_mock
    ):
        owner_id = uuid4()
        admin_id = uuid4()
        member_id = uuid4()
        company = make_company(owner_id, members=[make_member(admin_id, CompanyRole.ADMIN)])
        company_repo_mock.get_company_with_members.return_value = company
        analytics_repo_mock.get_company_last_attempts.return_value = [
            make_row(user_id=member_id, last_completed_at=datetime(2026, 7, 10)),
        ]

        result = await service.get_company_last_attempts(uuid4(), make_user(admin_id))

        assert len(result) == 1
        assert result[0].user_id == member_id
        assert result[0].last_completed_at == datetime(2026, 7, 10).date()

    async def test_returns_empty_list_when_no_members_have_attempts(
        self, service, company_repo_mock, analytics_repo_mock
    ):
        owner_id = uuid4()
        company_repo_mock.get_company_with_members.return_value = make_company(owner_id)
        analytics_repo_mock.get_company_last_attempts.return_value = []

        result = await service.get_company_last_attempts(uuid4(), make_user(owner_id))

        assert result == []
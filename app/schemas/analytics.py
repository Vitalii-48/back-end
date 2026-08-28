# app/schemas/analytics.py
from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AnalyticsBaseModel(BaseModel):
    """Базова модель з увімкненою серіалізацією об'єктів/рядків (ORM-ready)"""
    model_config = ConfigDict(from_attributes=True)


class WeeklyScoreItem(AnalyticsBaseModel):
    """Один тиждень + середній бал за цей тиждень."""
    week_start: date
    average_score: float  # у відсотках, наприклад 87.5


class UserRatingResponse(AnalyticsBaseModel):
    """Загальний рейтинг користувача по всіх компаніях."""
    overall_average: float


class QuizAveragesResponse(AnalyticsBaseModel):
    """Середні бали користувача по одному квізу, розбиті по тижнях."""
    quiz_id: UUID
    quiz_title: str
    weekly_scores: list[WeeklyScoreItem]


class LastAttemptItem(AnalyticsBaseModel):
    """Квіз + дата останнього проходження."""
    quiz_id: UUID
    quiz_title: str
    last_completed_at: date | None


class MemberWeeklyAveragesResponse(AnalyticsBaseModel):
    """Один учасник компанії + його бали по тижнях."""
    user_id: UUID
    weekly_scores: list[WeeklyScoreItem]


class MemberLastAttemptItem(AnalyticsBaseModel):
    """Учасник компанії + дата його останньої спроби (будь-якого квізу)."""
    user_id: UUID
    last_completed_at: date | None
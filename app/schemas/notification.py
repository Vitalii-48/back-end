# app/schemas/notification.py
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.enums import NotificationStatus


class NotificationBaseModel(BaseModel):
    """Базова модель з увімкненою серіалізацією ORM-об'єктів."""
    model_config = ConfigDict(from_attributes=True)


class NotificationResponse(NotificationBaseModel):
    """Схема для повернення одного сповіщення."""
    id: uuid.UUID
    message: str
    status: NotificationStatus
    created_at: datetime


class NotificationListResponse(NotificationBaseModel):
    """Схема для повернення списку сповіщень з метаданими пагінації."""
    notifications: list[NotificationResponse]
    total: int
    
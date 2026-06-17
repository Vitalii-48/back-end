import uuid
from sqlalchemy import String, Boolean
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.database.base import Base
from app.database.mixins import TimestampMixin

from typing import TYPE_CHECKING
# Імпортуємо ТІЛЬКИ для підказок типів
if TYPE_CHECKING:
    from app.models.company import Company

class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    companies: Mapped[list["Company"]] = relationship("Company", back_populates="owner")
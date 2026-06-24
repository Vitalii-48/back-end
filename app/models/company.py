import uuid

from sqlalchemy import String, ForeignKey, Boolean, DateTime, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.database.mixins import TimestampMixin

from typing import TYPE_CHECKING
# Імпортуємо ТІЛЬКИ для підказок типів
if TYPE_CHECKING:
    from app.models.user import User



class Company(TimestampMixin, Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str|None] = mapped_column(String, nullable=True)

    # Поле видимості (hidden / visible)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)

    # Зв'язок з юзером (Owner)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    owner: Mapped["User"] = relationship(back_populates="companies")


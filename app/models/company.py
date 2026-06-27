import uuid

from sqlalchemy import String, ForeignKey, Boolean, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.database.mixins import TimestampMixin

# Імпортуємо ТІЛЬКИ для підказок типів
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.user import User
    from app.models.company_actions import CompanyMember, CompanyRequest


class Company(TimestampMixin, Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str|None] = mapped_column(String, nullable=True)

    #  Поле видимості (hidden / visible)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)

    #  Зв'язок з юзером (Owner)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    owner: Mapped["User"] = relationship(back_populates="companies")

    #  Учасники компанії (включно з Owner-ом як CompanyMember з роллю OWNER)
    members: Mapped[list["CompanyMember"]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )

    # Запрошення та запити на вступ до компанії
    requests: Mapped[list["CompanyRequest"]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )

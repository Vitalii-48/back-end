import uuid

from sqlalchemy import String, Boolean, UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.database.base import Base
from app.database.mixins import TimestampMixin

# Імпортуємо ТІЛЬКИ для підказок типів
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.company_actions import CompanyMember, CompanyRequest


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),primary_key=True, default=uuid.uuid4, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    companies: Mapped[list["Company"]] = relationship(
        "Company",
        back_populates="owner")

    #  Компанії, в яких користувач є членом (через CompanyMember)
    memberships: Mapped[list["CompanyMember"]] = relationship(
        "CompanyMember",
        back_populates="user")

    #  Запрошення/запити, де цей користувач є адресатом або ініціатором
    company_requests: Mapped[list["CompanyRequest"]] = relationship(
        "CompanyRequest",
        back_populates="user")
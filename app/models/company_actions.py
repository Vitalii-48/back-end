# app/models/company_actions.py

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint, Enum, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import TimestampMixin
from app.models.enums import RequestType, RequestStatus, CompanyRole

# Імпортуємо ТІЛЬКИ для підказок типів, щоб уникнути circular import
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.user import User


class CompanyMember(TimestampMixin, Base):
    """
    Таблиця учасників компанії.
    Один рядок = один факт "цей user є членом цієї company".
    """
    __tablename__ = "company_members"
    __table_args__ = (
        # Гарантує на рівні БД, що один user не може бути двічі членом
        # однієї і тієї ж company (захист від дублікатів).
        UniqueConstraint("company_id", "user_id", name="uq_company_member"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[CompanyRole] = mapped_column(
        Enum(CompanyRole),
        default=CompanyRole.MEMBER,
        nullable=False,
    )

    company: Mapped["Company"] = relationship(
        "Company",
        back_populates="members")

    user: Mapped["User"] = relationship(
        "User",
        back_populates="memberships")


class CompanyRequest(TimestampMixin, Base):
    """
    Таблиця "заявок": запрошення від Owner-а (INVITE) або
    запит від користувача на вступ (REQUEST).
    Статус показує поточний стан розгляду заявки.
    """
    __tablename__ = "company_requests"
    __table_args__ = (
        # Захищає від кількох одночасних PENDING-заявок
        # одного user до однієї company.
        UniqueConstraint("company_id", "user_id", "type", name="uq_company_request"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Тип запиту: інвайт чи реквест
    type: Mapped[RequestType] = mapped_column(
        Enum(RequestType), nullable=False)

    # Статус запиту
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus),
        default=RequestStatus.PENDING,
        nullable=False,
    )

    company: Mapped["Company"] = relationship(
        "Company",
        back_populates="requests")

    user: Mapped["User"] = relationship(
        "User",
        back_populates="company_requests")
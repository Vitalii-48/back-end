# app/models/quiz.py
import uuid

from sqlalchemy import String, ForeignKey, Boolean, UUID, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.models.company import Company


class Quiz(Base):
    """ Квіз — головна сутність. Належить до компанії і має список питань. """
    __tablename__ = 'quizzes'

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    company_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    frequency: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships (зв'язки) — SQLAlchemy підтягує пов'язані об'єкти
    company: Mapped["Company"] = relationship("Company", back_populates="quizzes")
    questions: Mapped[list["QuizQuestion"]] = relationship(
        "QuizQuestion",
        back_populates="quiz",
        cascade="all, delete-orphan",
        lazy="selectin"
    )


class QuizQuestion(Base):
    """ Питання — належить до квізу. Має список варіантів відповіді. """
    __tablename__ = 'quiz_questions'

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quiz_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    quiz: Mapped["Quiz"] = relationship(back_populates="questions")

    # Зв'язок один-до-багатьох: Питання -> Варіанти відповідей
    options: Mapped[list["QuizAnswerOption"]] = relationship(
        "QuizQuestion",
        back_populates="question",
        cascade="all, delete-orphan",
        lazy="selectin"
    )


class QuizAnswerOption(Base):
    """
    Варіант відповіді — належить до питання.
    is_correct — чи є ця відповідь правильною.
    Завдання вимагає підтримки КІЛЬКОХ правильних відповідей.
    """
    __tablename__ = "quiz_answer_options"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=False)
    text: Mapped[str] = mapped_column(String(255), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    question: Mapped["QuizQuestion"] = relationship(
        "QuizQuestion",
        back_populates="options")
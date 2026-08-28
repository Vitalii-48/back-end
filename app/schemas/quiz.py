# app/schemas/quiz.py
from pydantic import BaseModel, Field, field_validator
from uuid import UUID

# AnswerOption schemas ──────────────────────────────────────────────
class QuizAnswerOptionBase(BaseModel):
    text: str = Field(..., min_length=1, max_length=255, description="Текст варіанту відповіді")
    is_correct: bool = Field(default=False, description="Чи є ця відповідь правильною")

class QuizAnswerOptionCreate(QuizAnswerOptionBase):
    pass

class QuizAnswerOptionResponse(QuizAnswerOptionBase):
    id: UUID

    model_config = {"from_attributes": True}


# Question schemas ──────────────────────────────────────────────
class QuizQuestionBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=500, description="Текст питання")


class QuizQuestionCreate(QuizQuestionBase):
    options: list[QuizAnswerOptionCreate] = Field(..., description="Список варіантів відповідей")

    @field_validator("options")
    @classmethod
    def validate_options(cls, options: list[QuizAnswerOptionCreate]) -> list[QuizAnswerOptionCreate]:
        # Правило 1: Кількість відповідей від 2 до 4
        if not (2 <= len(options) <= 4):
            raise ValueError("Кожне питання повинно мати від 2 до 4 варіантів відповідей.")

        # Правило 2: Хоча б одна відповідь правильна
        has_correct = any(option.is_correct for option in options)
        if not has_correct:
            raise ValueError("У питанні повинен бути хоча б один правильний варіант відповіді.")

        return options


class QuizQuestionResponse(QuizQuestionBase):
    id: UUID
    options: list[QuizAnswerOptionResponse]

    model_config = {"from_attributes": True}


# Quiz schemas
class QuizBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255, description="Назва квізу")
    description: str | None = Field(default=None, max_length=255, description="Опис квізу")


class QuizCreateRequest(QuizBase):
    questions: list[QuizQuestionCreate] = Field(..., description="Список питань для квізу")

    @field_validator("questions")
    @classmethod
    def validate_questions(cls, questions: list[QuizQuestionCreate]) -> list[QuizQuestionCreate]:
        # Правило 3: Мінімум 2 питання в квізі
        if len(questions) < 2:
            raise ValueError("Квіз повинен містити мінімум 2 питання.")
        return questions


class QuizUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, max_length=255)
    questions: list[QuizQuestionCreate] | None = None

    @field_validator("questions")
    @classmethod
    def validate_questions(cls, questions: list[QuizQuestionCreate] | None) -> list[QuizQuestionCreate] | None:
        # Валідація спрацює тільки якщо фронтенд передав поле "questions"
        if questions is not None and len(questions) < 2:
            raise ValueError("Квіз повинен містити мінімум 2 питання.")
        return questions



# Схема, яку ми віддамо у відповідь клієнту
class QuizDetailResponse(QuizBase):
    id: UUID
    company_id: UUID
    questions: list[QuizQuestionResponse]
    frequency: int = Field(default=0, ge=0, description="Скільки разів квіз пройдено всіма користувачами")

    model_config = {"from_attributes": True}


# Схема для списку квізів (з пагінацією), щоб не тягнути всі питання на сторінку списку
class QuizShortResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    frequency: int = Field(default=0, ge=0, description="Скільки разів квіз пройдено всіма користувачами")

    model_config = {"from_attributes": True}


class QuizzesListResponse(BaseModel):
    quizzes: list[QuizShortResponse]
    total: int
    page: int
    per_page: int
# app/schemas/quiz_result.py

from pydantic import BaseModel
from uuid import UUID

class QuestionAnswerSubmit(BaseModel):
    question_id: UUID
    selected_option_ids: list[UUID]  # Список, бо правильних варіантів може бути кілька

class QuizSubmitRequest(BaseModel):
    answers: list[QuestionAnswerSubmit]

class QuizSubmitResponse(BaseModel):
    quiz_id: UUID
    correct_answers_count: int
    total_questions_count: int
    is_passed: bool  # Опціонально, можна вивести статус проходження
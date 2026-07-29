 # app/schemas/quiz_import.py
from pydantic import BaseModel, Field


class ParsedAnswerData(BaseModel):
    text: str = Field(min_length=1)
    is_correct: bool


class ParsedQuestionData(BaseModel):
    title: str = Field(min_length=1)
    answers: list[ParsedAnswerData] = Field(default_factory=list)


class ParsedQuizData(BaseModel):
    title: str = Field(min_length=1)
    description: str = ""
    frequency: int = Field(ge=0)
    questions: list[ParsedQuestionData] = Field(default_factory=list)
    source_row_start: int | None = None


class QuizValidationError(BaseModel):
    quiz_title: str
    row_number: int | None = None
    message: str


class ImportReport(BaseModel):
    created: list[str] = Field(default_factory=list)
    updated: list[str] = Field(default_factory=list)
    errors: list[QuizValidationError] = Field(default_factory=list)
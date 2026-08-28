# app/services/quiz_validator.py
from app.schemas.quiz_import import ParsedQuizData, QuizValidationError

MIN_QUESTIONS = 2
MIN_ANSWERS = 2
MAX_ANSWERS = 4


class QuizValidator:
    """
    Перевіряє бізнес-правила квіза з BE #11:
    мінімум 2 питання, мінімум 2 відповіді, хоча б 1 правильна.
    Не звертається до бази даних — чиста функція над ParsedQuizData.
    """

    @staticmethod
    def validate(quiz_data: ParsedQuizData) -> list[QuizValidationError]:
        errors: list[QuizValidationError] = []

        if len(quiz_data.questions) < MIN_QUESTIONS:
            errors.append(QuizValidationError(
                quiz_title=quiz_data.title,
                row_number=quiz_data.source_row_start,
                message=f"Quiz must have at least {MIN_QUESTIONS} questions, got {len(quiz_data.questions)}",
            ))

        for question in quiz_data.questions:
            if len(question.answers) < MIN_ANSWERS:
                errors.append(QuizValidationError(
                    quiz_title=quiz_data.title,
                    row_number=quiz_data.source_row_start,
                    message=f"Question '{question.title}' must have at least {MIN_ANSWERS} answers",
                ))
            elif len(question.answers) > MAX_ANSWERS:
                errors.append(QuizValidationError(
                    quiz_title=quiz_data.title,
                    row_number=quiz_data.source_row_start,
                    message=f"Question '{question.title}' must have at most {MAX_ANSWERS} answers, got {len(question.answers)}",
                ))
            if not any(a.is_correct for a in question.answers):
                errors.append(QuizValidationError(
                    quiz_title=quiz_data.title,
                    row_number=quiz_data.source_row_start,
                    message=f"Question '{question.title}' has no correct answer",
                ))

        return errors
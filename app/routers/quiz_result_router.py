# app/routers/quiz_result_router.py
from uuid import UUID
from fastapi import APIRouter, Depends, status

from app.schemas.quiz_result import QuizSubmitRequest, QuizSubmitResponse
from app.services.quiz_result_service import QuizWorkflowService
from app.core.dependencies import get_current_user, get_quiz_result_service

router = APIRouter(prefix="/companies/{company_id}/quiz-workflow", tags=["Quiz Workflow"])


@router.post(
    "/{quiz_id}/submit",
    response_model=QuizSubmitResponse,
    status_code=status.HTTP_200_OK,
    summary="Надіслати відповіді на квіз",
)
async def submit_quiz(
    company_id: UUID,
    quiz_id: UUID,
    payload: QuizSubmitRequest,
    current_user=Depends(get_current_user),
    quiz_result_service: QuizWorkflowService = Depends(get_quiz_result_service),
):
    """
    Приймає відповіді користувача, підраховує результат і зберігає його в БД.
    """
    return await quiz_result_service.submit_quiz(
        company_id=company_id,
        user_id=current_user.id,
        quiz_id=quiz_id,
        payload=payload,
    )


@router.get(
    "/members/{user_id}/average-score",
    response_model=float,
    status_code=status.HTTP_200_OK,
    summary="Середній бал конкретного юзера в цій компанії",
)
async def get_user_average_in_company(
    company_id: UUID,
    user_id: UUID,
    current_user=Depends(get_current_user),
    quiz_result_service: QuizWorkflowService = Depends(get_quiz_result_service),
):
    """
    Повертає середній бал користувача в межах конкретної компанії.
    Доступно для owner/admin компанії (Таска BE #10).
    """
    return await quiz_result_service.get_user_average_in_company(
        user_id=user_id,
        company_id=company_id,
        requesting_user_id=current_user.id,
    )
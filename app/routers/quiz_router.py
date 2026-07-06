from uuid import UUID
from fastapi import APIRouter, Depends, status, Query

from app.models.user import User
from app.schemas.quiz import QuizCreateRequest, QuizUpdateRequest, QuizzesListResponse, QuizDetailResponse
from app.services.quiz_service import QuizService
from app.core.dependencies import get_current_user, get_quiz_service

router = APIRouter(prefix="/companise/{company_id}/quizzes", tags=["Quizzes"])


@router.post(
    "",
    response_model=QuizDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Створити новий квіз для компанії",
)
async def create_quiz(
    company_id: UUID,
    data: QuizCreateRequest,
    current_user: User = Depends(get_current_user),
    quiz_service: QuizService = Depends(get_quiz_service),
):
    """
    Створює новий квіз разом із питаннями та варіантами відповідей.
    Доступно тільки для OWNER або ADMIN цієї компанії.
    """
    return await quiz_service.create_company_quiz(
        company_id=company_id, data=data, user_id=current_user.id
    )


@router.get(
    "",
    response_model=QuizzesListResponse,
    status_code=status.HTTP_200_OK,
    summary="Отримати список квізів компанії з пагінацією",
)
async def get_quizzes(
    company_id: UUID,
    page: int = Query(default=1, ge=1, description="Номер сторінки"),
    size: int = Query(default=10, ge=1, le=100, description="Кількість елементів на сторінці"),
    current_user: User = Depends(get_current_user),
    quiz_service: QuizService = Depends(get_quiz_service),
):
    """
    Повертає пагінований список квізів.
    Поля квізу не містять вкладених питань (використовується QuizShortResponse).
    """
    return await quiz_service.get_company_quizzes_list(
        company_id=company_id,
        user_id=current_user.id,
        page=page,
        size=size
    )


@router.get(
    "/{quiz_id}",
    response_model=QuizDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Отримати деталі квізу",
)
async def get_quiz(
    company_id: UUID,
    quiz_id: UUID,
    current_user: User = Depends(get_current_user),
    quiz_service: QuizService = Depends(get_quiz_service),
):
    """
    Повертає повну інформацію про квіз включно з питаннями та варіантами відповідей.
    Доступно для будь-якого члена (member — учасник) компанії.
    """
    return await quiz_service.get_quiz_detail(
        quiz_id=quiz_id,
        company_id=company_id,
        user_id=current_user.id,
    )

@router.patch(
    "/{quiz_id}",
    response_model=QuizDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Оновити квіз компанії",
)
async def update_quiz(
    company_id: UUID,
    quiz_id: UUID,
    data: QuizUpdateRequest,
    current_user: User = Depends(get_current_user),
    quiz_service: QuizService = Depends(get_quiz_service),
):
    """
    Оновлює текстові поля квізу.
    Якщо передано масив 'questions' — старі питання повністю видаляються, а замість них записуються нові.
    """
    return await quiz_service.update_company_quiz(
        quiz_id=quiz_id, company_id=company_id, data=data, user_id=current_user.id
    )


@router.delete(
    "/{quiz_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Видалити квіз компанії",
)
async def delete_quiz(
    company_id: UUID,
    quiz_id: UUID,
    current_user: User = Depends(get_current_user),
    quiz_service: QuizService = Depends(get_quiz_service),
):
    """
    Повністю видаляє квіз з бази даних.
    Завдяки налаштованим каскадам у БД, також автоматично видаляються всі пов'язані питання та відповіді.
    """
    await quiz_service.delete_company_quiz(
        quiz_id=quiz_id, company_id=company_id, user_id=current_user.id
    )
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query, HTTPException
from fastapi import UploadFile, File

from app.core.dependencies import get_current_user, get_quiz_service
from app.core.dependencies import get_quiz_import_service

from app.models.user import User
from app.schemas.quiz_import import ImportReport
from app.schemas.quiz import QuizCreateRequest, QuizUpdateRequest, QuizzesListResponse, QuizDetailResponse
from app.services.quiz_service import QuizService
from app.services.quiz_import_service import QuizImportService

router = APIRouter(prefix="/companies/{company_id}/quizzes", tags=["Quizzes"])

MAX_IMPORT_FILE_SIZE = 5 * 1024 * 1024  # 5 МБ у байтах
ALLOWED_IMPORT_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


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
    per_page: int = Query(default=10, ge=1, le=100, description="Кількість елементів на сторінці"),
    current_user: User = Depends(get_current_user),
    quiz_service: QuizService = Depends(get_quiz_service),
):
    """
    Повертає пагінований список квізів.
    """
    return await quiz_service.get_company_quizzes_list(
        company_id=company_id,
        user_id=current_user.id,
        page=page,
        per_page=per_page
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
    Доступно для будь-якого члена компанії.
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
    """
    await quiz_service.delete_company_quiz(
        quiz_id=quiz_id, company_id=company_id, user_id=current_user.id
    )


@router.post(
    "/import",
    response_model=ImportReport,
    status_code=status.HTTP_200_OK,
    summary="Імпортувати квізи з Excel-файлу",
)
async def import_quizzes(
    company_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    quiz_import_service: QuizImportService = Depends(get_quiz_import_service),
):
    """
    Імпортує квізи з Excel-файлу: створює нові або оновлює існуючі
    (за співпадінням назви квізу в межах компанії).
    Доступно тільки для OWNER або ADMIN цієї компанії.
    """
    if file.content_type != ALLOWED_IMPORT_CONTENT_TYPE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл повинен бути у форматі .xlsx",
        )

    file_content = bytearray()
    while chunk := await file.read(1024 * 1024):
        file_content.extend(chunk)
        if len(file_content) > MAX_IMPORT_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Файл занадто великий. Максимум 5 МБ",
            )
    return await quiz_import_service.import_quizzes(
        company_id=company_id, file_content=file_content, user_id=current_user.id
    )
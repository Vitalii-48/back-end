from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.core.dependencies import get_export_service, get_current_user
from app.models.user import User
from app.services.export_service import ExportService

router = APIRouter(prefix="/quiz-results", tags=["Data Export"])


@router.get("/me/export")
async def export_my_results(
        export_format: Literal["json", "csv"] = "json",
        company_id: UUID | None = Query(None, description="Фільтр за конкретною компанією"),
        quiz_id: UUID | None = Query(None, description="Фільтр за конкретним квізом"),
        current_user: User = Depends(get_current_user),
        service: ExportService = Depends(get_export_service),
):
    """Користувач експортує СВОЇ особисті результати проходження квізів."""
    result = await service.export_my_results(
        requester_id=current_user.id,
        company_id=company_id,
        quiz_id=quiz_id,
        export_format=export_format,
    )

    if export_format == "csv":
        return StreamingResponse(
            result,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=my_quiz_results.csv"},
        )

    return result


@router.get("/companies/{company_id}/export")
async def export_company_results(
        company_id: UUID,
        export_format: Literal["json", "csv"] = "json",
        user_id: UUID | None = Query(None, description="ID користувача, чиї дані експортуємо (тільки для Admin/Owner)"),
        quiz_id: UUID | None = Query(None, description="Фільтр за конкретним квізом"),
        current_user: User = Depends(get_current_user),
        service: ExportService = Depends(get_export_service),
):
    """Owner/Admin (власник/адміністратор) компанії експортує результати квізів."""
    result = await service.export_company_quiz_results(
        company_id=company_id,
        requester_id=current_user.id,
        target_user_id=user_id,
        quiz_id=quiz_id,
        export_format=export_format,
    )

    if export_format == "csv":
        return StreamingResponse(
            result,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=company_{company_id}_results.csv"},
        )

    return result
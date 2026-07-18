# app/routers/notification_router.py
import uuid
from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user, get_notification_service
from app.models import User
from app.schemas.notification import NotificationListResponse, NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/", response_model=NotificationListResponse)
async def get_my_notifications(
        skip: int = Query(0, ge=0, description="Кількість елементів для пропуску"),
        limit: int = Query(10, ge=1, le=100, description="Кількість елементів на сторінці"),
        current_user: User = Depends(get_current_user),
        service: NotificationService = Depends(get_notification_service),
):

    notifications_list, total_count = await service.get_user_notifications(
        user_id=current_user.id,
        skip=skip,
        limit=limit)

    return NotificationListResponse.model_validate({
        "notifications": notifications_list,
        "total": total_count
    })


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_as_read(
        notification_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        service: NotificationService = Depends(get_notification_service),
):
    return await service.mark_as_read(notification_id, current_user.id)
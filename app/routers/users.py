from fastapi import APIRouter, Depends, status, Query
from uuid import UUID

from app.core.dependencies import get_current_user, get_user_service
from app.models import User
from app.services.user_service import UserService
from app.schemas.user import SignUpRequest, UserUpdateRequest, UserDetailResponse, UsersListResponse

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/", response_model=UsersListResponse)
async def get_users(
    page: int = Query(default=1, ge=1, description="Номер сторінки (page number)"),
    per_page: int = Query(default=10, ge=1, le=100, description="Кількість на сторінці"),
    user_service: UserService = Depends(get_user_service),
):
    db_users, total = await user_service.get_all_users(page, per_page)
    users = [UserDetailResponse.model_validate(user) for user in db_users]
    return UsersListResponse(users=users, total=total)


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: UUID,
    user_service: UserService = Depends(get_user_service)
):
    return await user_service.get_user_by_id(user_id)

@router.post("/", response_model=UserDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: SignUpRequest,
    user_service: UserService = Depends(get_user_service)
):
    return await user_service.create_user(data)

@router.patch("/{user_id}", response_model=UserDetailResponse)
async def update_user(
    user_id: UUID,
    data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.update_user(user_id, data, current_user)

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    user_service:UserService = Depends(get_user_service)
):
    await user_service.delete_user(user_id, current_user)
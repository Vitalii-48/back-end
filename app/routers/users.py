from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db_postgres import get_db_postgres
from app.services.user_service import UserService
from app.schemas.user import SignUpRequest, UserUpdateRequest, UserDetailResponse, UsersListResponse

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/", response_model=UsersListResponse)
async def get_users(
    page: int = Query(default=1, ge=1, description="Номер сторінки (page number)"),
    per_page: int = Query(default=10, ge=1, le=100, description="Кількість на сторінці"),
    db: AsyncSession = Depends(get_db_postgres),
):
    users, total = await UserService(db).get_all_users(page, per_page)
    return UsersListResponse(users=users, total=total)

@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db_postgres)):
    return await UserService(db).get_user_by_id(user_id)

@router.post("/", response_model=UserDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_user(data: SignUpRequest, db: AsyncSession = Depends(get_db_postgres)):
    return await UserService(db).create_user(data)

@router.patch("/{user_id}", response_model=UserDetailResponse)
async def update_user(
    user_id: int,
    data: UserUpdateRequest,
    db: AsyncSession = Depends(get_db_postgres),
):
    return await UserService(db).update_user(user_id, data)

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db_postgres)):
    await UserService(db).delete_user(user_id)
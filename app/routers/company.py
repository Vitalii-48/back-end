from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.schemas.company import  CompanyCreateRequest, CompanyUpdateRequest, CompanyDetailResponse, CompaniesListResponse
from app.models.user import User
from app.core.dependencies import get_current_user, get_company_service
from app.services.company_service import CompanyService

router = APIRouter(prefix="/company", tags=["Company"])

@router.post("/", response_model=CompanyDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    data: CompanyCreateRequest,
    current_user: User = Depends(get_current_user),
    company_service:CompanyService = Depends(get_company_service),
):
    """Створення компанії. Авторизований користувач автоматично стає Owner."""
    return await company_service.create_company(data, current_user)

@router.get("/", response_model=CompaniesListResponse)
async def get_companies(
    page: int = Query(default=1, ge=1, description="Номер сторінки"),
    per_page: int = Query(default=10, ge=1, le=100, description="Кількість на сторінці"),
    company_service: CompanyService = Depends(get_company_service),
):
    return await company_service.get_all_companies(page, per_page)


@router.get("/{company_id}", response_model=CompanyDetailResponse)
async def get_company(
    company_id: UUID,
    current_user: User | None = Depends(get_current_user),
    company_service: CompanyService = Depends(get_company_service),
):
    """Отримання деталей компанії за її ID"""
    return await company_service.get_company(company_id, current_user)

@router.patch("/{company_id}", response_model=CompanyDetailResponse)
async def update_company(
    company_id: UUID,
    data: CompanyUpdateRequest,
    current_user: User = Depends(get_current_user),
    company_service: CompanyService = Depends(get_company_service),
):
    return await company_service.update_company(company_id, data, current_user)

@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: UUID,
    current_user: User = Depends(get_current_user),
    company_service: CompanyService = Depends(get_company_service),
):
    await company_service.delete_company(company_id, current_user)
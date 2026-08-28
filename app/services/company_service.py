from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import CompanyRole
from app.models.company import Company
from app.repositories.company_repository import CompanyRepository
from app.repositories.company_member_repository import CompanyMemberRepository
from app.models.user import User
import logging

from app.schemas.company import CompanyCreateRequest, CompanyDetailResponse, CompaniesListResponse, CompanyUpdateRequest

logger = logging.getLogger(__name__)

class CompanyService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = CompanyRepository(session)
        self.members_repo = CompanyMemberRepository(session)


    async def create_company(self, data: CompanyCreateRequest, current_user: User) -> CompanyDetailResponse:
        existing_company = await self.repo.get_company_by_name(data.name)
        if existing_company:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Company with name '{data.name}' already exists."
            )

        try:
            company = await self.repo.create_company(
                data=data,
                owner_id=current_user.id,
            )

            await self.members_repo.create_member(
                company_id=company.id,
                user_id=current_user.id,
                role=CompanyRole.OWNER,
            )

            await self.session.commit()

            await self.session.refresh(company)

            return CompanyDetailResponse.model_validate(company)

        except Exception:
            await self.session.rollback()
            raise


    async def get_company(self, company_id: UUID, current_user: User | None = None) -> Company:
        company = await self.repo.get_company_by_id(company_id)

        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with id={company_id} not found")

        if not company.is_visible:
            if current_user is None or company.owner_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Company not found",
                )

        return company


    async def update_company(
        self,
        company_id: UUID,
        data: CompanyUpdateRequest,
        current_user: User,
    ) -> CompanyDetailResponse:

        company = await self.repo.get_company_by_id(company_id)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        if company.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        update_data = data.model_dump(exclude_none=True)
        for field, value in update_data.items():
            setattr(company, field, value)
        updated = await self.repo.update_company(company)
        logger.info(f"User {current_user.id} updated company {company_id}")
        return CompanyDetailResponse.model_validate(updated)


    async def get_all_companies(self, page: int, per_page: int) -> CompaniesListResponse:
        """Отримання списку компаній з пагінацією"""
        skip = (page - 1) * per_page
        limit = per_page
        companies, total = await self.repo.get_all_companies(skip=skip, limit=limit)
        return CompaniesListResponse(
            companies=[CompanyDetailResponse.model_validate(c) for c in companies],
            total=total,
        )


    async def delete_company(self, company_id: UUID, current_user: User):
        company = await self.repo.get_company_by_id(company_id)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        if company.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        await self.repo.delete_company(company)
        logger.info(f"User {current_user.id} deleted company: {company_id}")





from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import CompanyRole
from app.models.company import Company
from app.models.company_actions import CompanyMember
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
        company = Company(
            name=data.name,
            description=data.description,
            is_visible=data.is_visible,
            owner_id=current_user.id,
        )
        self.session.add(company)
        # flush() надсилає INSERT у базу і генерує company.id,
        # але ЩЕ НЕ фіксує транзакцію - її можна повністю відкотити.
        await self.session.flush()

        owner_membership = CompanyMember(
            company_id=company.id,
            user_id=current_user.id,
            role=CompanyRole.OWNER,
        )
        self.session.add(owner_membership)

        # Один COMMIT на обидва записи: або Company + CompanyMember
        # збережуться РАЗОМ, або (при помилці) відкотяться РАЗОМ.
        await self.session.commit()
        await self.session.refresh(company)

        logger.info(f"User {current_user.id} created company: {company.name}")
        return CompanyDetailResponse.model_validate(company)


    async def get_company(self, company_id: UUID) -> Company:
        company = await self.repo.get_company_by_id(company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with id={company_id} not found")
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





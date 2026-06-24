import logging
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.company import Company


logger = logging.getLogger(__name__)

class CompanyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_company(self, company: Company) -> Company:
        """Запис нової компанії в базу даних"""
        self.session.add(company)
        await self.session.commit()
        await self.session.refresh(company)
        return company

    async def update_company(self, company: Company) -> Company:
        await self.session.commit()
        await self.session.refresh(company)
        return company

    async def delete_company(self, company: Company) -> None:
        await self.session.delete(company)
        await self.session.commit()


    async def get_company_by_id(self, company_id: UUID) -> Company | None:
        """Пошук компанії за id"""
        result = await self.session.execute(
            select(Company).where(Company.id == company_id)
        )
        return result.scalar_one_or_none()

    async def get_all_companies(self, skip: int = 0, limit: int = 10) -> tuple[list[Company], int]:
        result = await self.session.execute(
            select(Company)
            .where(Company.is_visible == True)
            .offset(skip).limit(limit)
        )
        companies = list(result.scalars().all())
        # Рахуємо загальну кількість
        total = await self.session.scalar(
            select(func.count(Company.id))
            .where(Company.is_visible == True))
        logger.debug(f"Fetched {len(companies)} companies, total={total}")
        return companies, total or 0

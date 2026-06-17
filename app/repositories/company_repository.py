import logging
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.company import Company


logger = logging.getLogger(__name__)

class CompanyRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create_company(self, company: Company) -> Company:
        """Запис нової компанії в базу даних"""
        self.db_session.add(company)
        await self.db_session.commit()
        await self.db_session.refresh(company)
        return company

    async def update_company(self, company: Company) -> Company:
        await self.db_session.commit()
        await self.db_session.refresh(company)
        return company

    async def delete_company(self, company: Company) -> None:
        await self.db_session.delete(company)
        await self.db_session.commit()


    async def get_company_by_id(self, company_id: UUID) -> Company | None:
        """Пошук компанії за ID"""
        result = await self.db_session.execute(
            select(Company).where(Company.id == company_id)
        )
        return result.scalar_one_or_none()

    async def get_all_companies(self, skip: int = 0, limit: int = 10) -> tuple[list[Company], int]:
        result = await self.db_session.execute(
            select(Company).offset(skip).limit(limit)
        )
        companies = list(result.scalars().all())
        # Рахуємо загальну кількість (total count)
        total = await self.db_session.scalar(select(func.count(Company.id)))
        logger.debug(f"Fetched {len(companies)} companies, total={total}")
        return companies, total or 0

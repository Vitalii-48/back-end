import logging
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.schemas.company import CompanyCreateRequest
from sqlalchemy.orm import selectinload  

logger = logging.getLogger(__name__)

class CompanyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_company(self, data: CompanyCreateRequest, owner_id: UUID) -> Company:
        """Запис нової компанії в базу даних"""
        company = Company(
            name=data.name,
            description=data.description,
            is_visible=data.is_visible,
            owner_id=owner_id,
        )
        self.session.add(company)
        # flush() надсилає INSERT у базу і генерує company.id,
        # але ЩЕ НЕ фіксує транзакцію - її можна повністю відкотити.
        await self.session.flush()

        return company


    async def update_company(self, company: Company) -> Company:
        await self.session.commit()
        await self.session.refresh(company)
        return company


    async def delete_company(self, company: Company) -> None:
        await self.session.delete(company)
        await self.session.commit()

    async def get_company_by_name(self, name: str) -> Company | None:
        """Пошук компанії за назвою (для валідації унікальності)"""
        result = await self.session.execute(
            select(Company).where(Company.name == name)
        )
        return result.scalar_one_or_none()

    async def get_company_by_id(self, company_id: UUID) -> Company | None:
        """Пошук компанії за id"""
        result = await self.session.execute(
            select(Company).where(Company.id == company_id)
        )
        return result.scalar_one_or_none()


    async def get_company_with_members(self, company_id: UUID) -> Company | None:
        """Пошук компанії разом із завантаженим списком учасників (members).
        Потрібно для перевірки прав owner/admin без додаткового запиту до бази."""
        result = await self.session.execute(
            select(Company)
            .options(selectinload(Company.members))
            .where(Company.id == company_id)
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

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID

class CompanyBase(BaseModel):
    name: str = Field(
        ...,
        description="Унікальне ім'я компанії",
        examples=["Company name"],
        min_length=1,
        max_length=255)
    description: str | None = None


class CompanyCreateRequest(CompanyBase):
    is_visible: bool  = True


class CompanyUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=255)
    is_visible: bool | None = None


class CompanyDetailResponse(CompanyBase):
    id: UUID
    owner_id: UUID
    is_visible: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompaniesListResponse(BaseModel):
    companies: list[CompanyDetailResponse]
    total: int
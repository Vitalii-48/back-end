# app/schemas/company_actions.py

from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import RequestType, RequestStatus, CompanyRole


# ───────────────────── Membership (CompanyMember) ─────────────────────

class CompanyMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    user_id: UUID
    role: CompanyRole
    created_at: datetime


class CompanyMembersListResponse(BaseModel):
    members: list[CompanyMemberResponse]
    total: int


# ───────────────────── Requests / Invitations (CompanyRequest) ─────────────────────

class CompanyInviteCreateRequest(BaseModel):
    """Те, що Owner надсилає, коли запрошує конкретного юзера."""
    user_id: UUID


class CompanyRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    user_id: UUID
    type: RequestType
    status: RequestStatus
    created_at: datetime


class CompanyRequestsListResponse(BaseModel):
    requests: list[CompanyRequestResponse]
    total: int
    

class CompanyAdminsListResponse(BaseModel):
    admins: list[CompanyMemberResponse]
    total: int
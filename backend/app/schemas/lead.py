from math import ceil
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.customer import CustomerOwnerResponse, normalize_phone


LeadStatus = Literal["new", "contacted", "qualified", "unqualified", "converted", "lost"]
LeadPriority = Literal["low", "medium", "high"]


class LeadBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=7, max_length=32)
    company_name: str | None = Field(default=None, max_length=150)
    source: str = Field(min_length=1, max_length=100)
    priority: LeadPriority = "medium"
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("name", "source")
    @classmethod
    def required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field is required.")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        return str(value).strip().lower() if value else None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        return normalize_phone(value) if value else None

    @field_validator("company_name", "notes")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value else None


class LeadCreate(LeadBase):
    owner_id: UUID | None = None


class LeadUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=7, max_length=32)
    company_name: str | None = Field(default=None, max_length=150)
    source: str | None = Field(default=None, min_length=1, max_length=100)
    priority: LeadPriority | None = None
    notes: str | None = Field(default=None, max_length=2000)
    owner_id: UUID | None = None

    @field_validator("name", "source")
    @classmethod
    def required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("This field is required.")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        return str(value).strip().lower() if value else None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        return normalize_phone(value) if value else None

    @field_validator("company_name", "notes")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value else None


class LeadStatusChange(BaseModel):
    status: Literal["contacted", "qualified", "unqualified", "lost"]


class LeadOwnerResponse(CustomerOwnerResponse):
    pass


class LeadListItem(BaseModel):
    id: UUID
    lead_code: str
    name: str
    email: EmailStr | None
    phone: str | None
    source: str
    status: LeadStatus
    priority: LeadPriority
    owner: LeadOwnerResponse | None


class LeadResponse(LeadListItem):
    company_name: str | None
    notes: str | None
    converted_customer_id: UUID | None


class LeadPage(BaseModel):
    items: list[LeadListItem]
    page: int
    page_size: int
    total: int
    total_pages: int

    @classmethod
    def create(cls, *, items: list[LeadListItem], page: int, page_size: int, total: int) -> "LeadPage":
        return cls(items=items, page=page, page_size=page_size, total=total, total_pages=ceil(total / page_size) if total else 0)


class LeadHistoryItem(BaseModel):
    id: UUID
    action: str
    result: str
    created_at: str
    actor_id: UUID | None
    details: str | None


class LeadConversionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lead: LeadResponse
    customer_id: UUID

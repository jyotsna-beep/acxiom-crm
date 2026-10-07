from math import ceil
import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


CustomerStatus = Literal["active", "inactive"]
PHONE_ALLOWED = re.compile(r"^[0-9+()\-\s.]+$")


def normalize_phone(value: str) -> str:
    value = value.strip()
    if not PHONE_ALLOWED.fullmatch(value):
        raise ValueError("Enter a valid phone number.")
    digits = "".join(character for character in value if character.isdigit())
    if not 7 <= len(digits) <= 15:
        raise ValueError("Enter a valid phone number.")
    return f"+{digits}"


class CustomerBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=32)
    address: str | None = Field(default=None, max_length=500)
    status: CustomerStatus = "active"
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Customer name is required.")
        return normalized

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_phone(value)

    @field_validator("address", "notes")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value else None


class CustomerCreate(CustomerBase):
    owner_id: UUID | None = None


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=7, max_length=32)
    address: str | None = Field(default=None, max_length=500)
    status: CustomerStatus | None = None
    notes: str | None = Field(default=None, max_length=2000)
    owner_id: UUID | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Customer name is required.")
        return normalized

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        return str(value).strip().lower() if value else None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        return normalize_phone(value) if value else None

    @field_validator("address", "notes")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value else None


class CustomerOwnerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str | None
    email: EmailStr


class CustomerListItem(BaseModel):
    id: UUID
    customer_code: str
    name: str
    email: EmailStr
    phone: str
    status: CustomerStatus
    owner: CustomerOwnerResponse | None


class CustomerResponse(CustomerListItem):
    address: str | None
    notes: str | None


class CustomerPage(BaseModel):
    items: list[CustomerListItem]
    page: int
    page_size: int
    total: int
    total_pages: int

    @classmethod
    def create(cls, *, items: list[CustomerListItem], page: int, page_size: int, total: int) -> "CustomerPage":
        return cls(items=items, page=page, page_size=page_size, total=total, total_pages=ceil(total / page_size) if total else 0)


class CustomerHistoryItem(BaseModel):
    id: UUID
    action: str
    result: str
    created_at: str
    actor_id: UUID | None
    details: str | None


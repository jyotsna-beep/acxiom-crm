from datetime import date
from decimal import Decimal
from math import ceil
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator
from app.schemas.customer import CustomerOwnerResponse

OpportunityStage = Literal["qualification", "proposal", "negotiation", "won", "lost"]

class OpportunityBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    customer_id: UUID
    lead_id: UUID | None = None
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    probability: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    expected_close_date: date
    source: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def required_name(cls, value: str) -> str:
        value = value.strip()
        if not value: raise ValueError("Opportunity name is required.")
        return value

    @field_validator("source", "notes")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        return value.strip() if value else None

class OpportunityCreate(OpportunityBase):
    owner_id: UUID | None = None

class OpportunityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    customer_id: UUID | None = None
    lead_id: UUID | None = None
    amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    probability: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    expected_close_date: date | None = None
    source: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)
    owner_id: UUID | None = None

    @field_validator("name")
    @classmethod
    def required_name(cls, value: str | None) -> str | None:
        if value is None: return None
        value = value.strip()
        if not value: raise ValueError("Opportunity name is required.")
        return value

    @field_validator("source", "notes")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        return value.strip() if value else None

class OpportunityStageChange(BaseModel):
    stage: Literal["proposal", "negotiation", "won", "lost"]

class OpportunityOwnerResponse(CustomerOwnerResponse): pass

class OpportunityListItem(BaseModel):
    id: UUID; opportunity_code: str; name: str; customer_id: UUID; customer_name: str
    lead_id: UUID | None; amount: Decimal; probability: Decimal; weighted_pipeline: Decimal
    stage: OpportunityStage; expected_close_date: date; owner: OpportunityOwnerResponse | None

class OpportunityResponse(OpportunityListItem):
    source: str | None; notes: str | None

class OpportunityPage(BaseModel):
    items: list[OpportunityListItem]; page: int; page_size: int; total: int; total_pages: int
    @classmethod
    def create(cls, *, items, page, page_size, total):
        return cls(items=items, page=page, page_size=page_size, total=total, total_pages=ceil(total / page_size) if total else 0)

class OpportunityHistoryItem(BaseModel):
    id: UUID; action: str; result: str; created_at: str; actor_id: UUID | None; details: str | None

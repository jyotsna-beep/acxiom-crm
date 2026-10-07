from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_csrf
from app.core.database import get_db
from app.models.user import User
from app.schemas.lead import LeadConversionResponse, LeadCreate, LeadHistoryItem, LeadOwnerResponse, LeadPage, LeadResponse, LeadStatusChange, LeadUpdate
from app.services.lead_service import convert_lead, create_lead, get_lead, lead_history, list_assignable_owners, list_leads, transition_lead_status, update_lead

router = APIRouter(prefix="/api/leads", tags=["leads"])
def _ip(request: Request) -> str | None: return request.client.host if request.client else None

@router.get("", response_model=LeadPage)
def list_lead_records(search: str | None = Query(default=None, max_length=150), lead_status: Literal["new", "contacted", "qualified", "unqualified", "converted", "lost"] | None = Query(default=None, alias="status"), priority: Literal["low", "medium", "high"] | None = None, owner_id: UUID | None = None, page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100), sort_by: Literal["name", "status", "priority", "source", "created_at", "lead_code"] = "name", sort_order: Literal["asc", "desc"] = "asc", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> LeadPage:
    return list_leads(db, current_user=current_user, search=search, lead_status=lead_status, priority=priority, owner_id=owner_id, page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order)

@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead_record(payload: LeadCreate, request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_csrf)) -> LeadResponse:
    return create_lead(db, current_user=current_user, payload=payload, ip_address=_ip(request))

@router.get("/owners", response_model=list[LeadOwnerResponse])
def owners(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[LeadOwnerResponse]:
    return list_assignable_owners(db, current_user=current_user)

@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead_record(lead_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> LeadResponse:
    return get_lead(db, current_user=current_user, lead_id=lead_id)

@router.put("/{lead_id}", response_model=LeadResponse)
def update_lead_record(lead_id: UUID, payload: LeadUpdate, request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_csrf)) -> LeadResponse:
    return update_lead(db, current_user=current_user, lead_id=lead_id, payload=payload, ip_address=_ip(request))

@router.post("/{lead_id}/status", response_model=LeadResponse)
def change_status(lead_id: UUID, payload: LeadStatusChange, request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_csrf)) -> LeadResponse:
    return transition_lead_status(db, current_user=current_user, lead_id=lead_id, payload=payload, ip_address=_ip(request))

@router.post("/{lead_id}/convert", response_model=LeadConversionResponse)
def convert_lead_record(lead_id: UUID, request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_csrf)) -> LeadConversionResponse:
    return convert_lead(db, current_user=current_user, lead_id=lead_id, ip_address=_ip(request))

@router.get("/{lead_id}/history", response_model=list[LeadHistoryItem])
def history(lead_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[LeadHistoryItem]:
    return lead_history(db, current_user=current_user, lead_id=lead_id)

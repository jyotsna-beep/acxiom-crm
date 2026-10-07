from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.audit_log import AuditLog
from app.models.lead import Lead
from app.models.user import User
from app.policies.authorization import authorized_user_ids, can_access_owner
from app.schemas.customer import CustomerCreate
from app.schemas.lead import LeadConversionResponse, LeadCreate, LeadHistoryItem, LeadListItem, LeadOwnerResponse, LeadPage, LeadResponse, LeadStatusChange, LeadUpdate
from app.services.audit_service import write_audit
from app.services.customer_service import create_customer_for_conversion


# Terminal statuses cannot be edited. Converted is reached only through convert_lead.
ALLOWED_TRANSITIONS = {
    "new": {"contacted", "qualified", "unqualified", "lost"},
    "contacted": {"qualified", "unqualified", "lost"},
    "qualified": {"lost"},
    "unqualified": set(),
    "lost": set(),
    "converted": set(),
}


def _snapshot(lead: Lead) -> dict[str, str | None]:
    return {"lead_code": lead.lead_code, "name": lead.name, "source": lead.source, "status": lead.status, "priority": lead.priority, "owner_id": str(lead.owner_id) if lead.owner_id else None, "converted_customer_id": str(lead.converted_customer_id) if lead.converted_customer_id else None}


def _owner(owner: User | None) -> LeadOwnerResponse | None:
    return LeadOwnerResponse(id=owner.id, username=owner.username, email=owner.email) if owner else None


def _item(lead: Lead) -> LeadListItem:
    return LeadListItem(id=lead.id, lead_code=lead.lead_code, name=lead.name, email=lead.email, phone=lead.phone, source=lead.source or "", status=lead.status, priority=lead.priority or "medium", owner=_owner(lead.owner))


def _response(lead: Lead) -> LeadResponse:
    return LeadResponse(**_item(lead).model_dump(), company_name=lead.company_name, notes=lead.notes, converted_customer_id=lead.converted_customer_id)


def _lead_or_404(db: Session, lead_id: UUID) -> Lead:
    lead = db.scalar(select(Lead).options(joinedload(Lead.owner)).where(Lead.id == lead_id))
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return lead


def _require_access(db: Session, user: User, lead: Lead) -> None:
    if not can_access_owner(db, user, lead.owner_id):
        raise HTTPException(status_code=403, detail="You do not have access to this lead.")


def _owner_or_error(db: Session, user: User, requested_owner_id: UUID | None) -> User:
    owner_id = requested_owner_id or user.id
    if not can_access_owner(db, user, owner_id):
        raise HTTPException(status_code=403, detail="You cannot assign this lead to that owner.")
    owner = db.get(User, owner_id)
    if owner is None or not owner.is_active:
        raise HTTPException(status_code=400, detail="Lead owner must be an active user.")
    return owner


def list_leads(db: Session, *, current_user: User, search: str | None, lead_status: str | None, priority: str | None, owner_id: UUID | None, page: int, page_size: int, sort_by: str, sort_order: str) -> LeadPage:
    statement = select(Lead).options(joinedload(Lead.owner))
    scope = authorized_user_ids(db, current_user)
    if scope is not None:
        statement = statement.where(Lead.owner_id.in_(scope))
    if owner_id:
        if not can_access_owner(db, current_user, owner_id):
            raise HTTPException(status_code=403, detail="You cannot filter by that owner.")
        statement = statement.where(Lead.owner_id == owner_id)
    if lead_status:
        statement = statement.where(Lead.status == lead_status)
    if priority:
        statement = statement.where(Lead.priority == priority)
    if search:
        term = f"%{search.strip().lower()}%"
        statement = statement.where(or_(func.lower(Lead.name).like(term), func.lower(func.coalesce(Lead.email, "")).like(term), Lead.phone.like(term), func.lower(func.coalesce(Lead.company_name, "")).like(term), func.lower(Lead.source).like(term)))
    columns = {"name": Lead.name, "status": Lead.status, "priority": Lead.priority, "source": Lead.source, "created_at": Lead.created_at, "lead_code": Lead.lead_code}
    column = columns[sort_by]
    statement = statement.order_by(column.desc() if sort_order == "desc" else column.asc())
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    leads = db.scalars(statement.offset((page - 1) * page_size).limit(page_size)).unique().all()
    return LeadPage.create(items=[_item(lead) for lead in leads], page=page, page_size=page_size, total=total)


def list_assignable_owners(db: Session, *, current_user: User) -> list[LeadOwnerResponse]:
    statement = select(User).where(User.is_active.is_(True)).order_by(User.username.asc(), User.email.asc())
    scope = authorized_user_ids(db, current_user)
    if scope is not None:
        statement = statement.where(User.id.in_(scope))
    return [_owner(user) for user in db.scalars(statement).all()]


def get_lead(db: Session, *, current_user: User, lead_id: UUID) -> LeadResponse:
    lead = _lead_or_404(db, lead_id)
    _require_access(db, current_user, lead)
    return _response(lead)


def create_lead(db: Session, *, current_user: User, payload: LeadCreate, ip_address: str | None) -> LeadResponse:
    owner = _owner_or_error(db, current_user, payload.owner_id)
    lead = Lead(lead_code=f"LEAD-{uuid4().hex[:12].upper()}", name=payload.name, email=str(payload.email) if payload.email else None, phone=payload.phone, company_name=payload.company_name, source=payload.source, status="new", priority=payload.priority, notes=payload.notes, owner_id=owner.id)
    db.add(lead)
    db.flush()
    db.refresh(lead, attribute_names=["owner"])
    write_audit(db, actor_id=current_user.id, action="lead_created", entity_name="lead", record_id=lead.id, new_value=_snapshot(lead), ip_address=ip_address)
    db.commit()
    db.refresh(lead, attribute_names=["owner"])
    return _response(lead)


def update_lead(db: Session, *, current_user: User, lead_id: UUID, payload: LeadUpdate, ip_address: str | None) -> LeadResponse:
    lead = _lead_or_404(db, lead_id)
    _require_access(db, current_user, lead)
    if lead.status in {"converted", "lost", "unqualified"}:
        raise HTTPException(status_code=400, detail="Terminal leads cannot be edited.")
    updates = payload.model_dump(exclude_unset=True)
    if "owner_id" in updates:
        if updates["owner_id"] is None:
            raise HTTPException(status_code=400, detail="Lead owner is required.")
        updates["owner_id"] = _owner_or_error(db, current_user, updates["owner_id"]).id
    if not updates:
        return _response(lead)
    old_value = _snapshot(lead)
    for field, value in updates.items():
        setattr(lead, field, value)
    db.flush()
    db.refresh(lead, attribute_names=["owner"])
    action = "lead_assigned" if "owner_id" in updates else "lead_updated"
    write_audit(db, actor_id=current_user.id, action=action, entity_name="lead", record_id=lead.id, old_value=old_value, new_value=_snapshot(lead), ip_address=ip_address)
    db.commit()
    db.refresh(lead, attribute_names=["owner"])
    return _response(lead)


def transition_lead_status(db: Session, *, current_user: User, lead_id: UUID, payload: LeadStatusChange, ip_address: str | None) -> LeadResponse:
    lead = _lead_or_404(db, lead_id)
    _require_access(db, current_user, lead)
    if payload.status not in ALLOWED_TRANSITIONS[lead.status]:
        raise HTTPException(status_code=400, detail=f"Cannot transition a {lead.status} lead to {payload.status}.")
    old_value = _snapshot(lead)
    lead.status = payload.status
    db.flush()
    write_audit(db, actor_id=current_user.id, action="lead_status_changed", entity_name="lead", record_id=lead.id, old_value=old_value, new_value=_snapshot(lead), ip_address=ip_address)
    db.commit()
    db.refresh(lead, attribute_names=["owner"])
    return _response(lead)


def convert_lead(db: Session, *, current_user: User, lead_id: UUID, ip_address: str | None) -> LeadConversionResponse:
    lead = _lead_or_404(db, lead_id)
    _require_access(db, current_user, lead)
    if lead.status == "converted" or lead.converted_customer_id:
        raise HTTPException(status_code=409, detail="Lead has already been converted.")
    if lead.status != "qualified":
        raise HTTPException(status_code=400, detail="Only qualified leads can be converted.")
    if not lead.email or not lead.phone:
        raise HTTPException(status_code=400, detail="A qualified lead needs an email and phone before conversion.")
    customer = create_customer_for_conversion(db, current_user=current_user, payload=CustomerCreate(name=lead.name, email=lead.email, phone=lead.phone, status="active", notes=lead.notes, owner_id=lead.owner_id), ip_address=ip_address)
    old_value = _snapshot(lead)
    lead.converted_customer_id = customer.id
    lead.status = "converted"
    db.flush()
    write_audit(db, actor_id=current_user.id, action="lead_converted", entity_name="lead", record_id=lead.id, old_value=old_value, new_value=_snapshot(lead), details="Customer created from qualified lead.", ip_address=ip_address)
    db.commit()
    db.refresh(lead, attribute_names=["owner"])
    return LeadConversionResponse(lead=_response(lead), customer_id=customer.id)


def lead_history(db: Session, *, current_user: User, lead_id: UUID) -> list[LeadHistoryItem]:
    lead = _lead_or_404(db, lead_id)
    _require_access(db, current_user, lead)
    entries = db.scalars(select(AuditLog).where(AuditLog.entity_name == "lead", AuditLog.record_id == str(lead_id)).order_by(AuditLog.created_at.desc())).all()
    return [LeadHistoryItem(id=item.id, action=item.action, result=item.result, created_at=item.created_at.isoformat(), actor_id=item.user_id, details=item.details) for item in entries]

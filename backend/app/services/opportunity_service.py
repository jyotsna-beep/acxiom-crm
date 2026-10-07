from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.lead import Lead
from app.models.opportunity import Opportunity
from app.models.user import User
from app.policies.authorization import authorized_user_ids, can_access_owner
from app.schemas.opportunity import OpportunityCreate, OpportunityHistoryItem, OpportunityListItem, OpportunityOwnerResponse, OpportunityPage, OpportunityResponse, OpportunityStageChange, OpportunityUpdate
from app.services.audit_service import write_audit

ACTIVE_STAGES = {"qualification", "proposal", "negotiation"}
STAGE_TRANSITIONS = {"qualification": {"proposal", "lost"}, "proposal": {"negotiation", "lost"}, "negotiation": {"won", "lost"}, "won": set(), "lost": set()}

def _snapshot(item): return {"opportunity_code": item.opportunity_code, "name": item.name, "customer_id": str(item.customer_id), "lead_id": str(item.lead_id) if item.lead_id else None, "stage": item.stage, "owner_id": str(item.owner_id) if item.owner_id else None, "amount": str(item.amount), "probability": str(item.probability)}
def _owner(user): return OpportunityOwnerResponse(id=user.id, username=user.username, email=user.email) if user else None
def _weighted(item): return (Decimal(item.amount) * Decimal(item.probability) / Decimal("100")).quantize(Decimal("0.01"))
def _item(item): return OpportunityListItem(id=item.id, opportunity_code=item.opportunity_code, name=item.name, customer_id=item.customer_id, customer_name=item.customer.name, lead_id=item.lead_id, amount=item.amount, probability=item.probability, weighted_pipeline=_weighted(item), stage=item.stage, expected_close_date=item.expected_close_date, owner=_owner(item.owner))
def _response(item): return OpportunityResponse(**_item(item).model_dump(), source=item.source, notes=item.notes)
def _get(db, opportunity_id):
    item = db.scalar(select(Opportunity).options(joinedload(Opportunity.owner), joinedload(Opportunity.customer)).where(Opportunity.id == opportunity_id))
    if not item: raise HTTPException(404, "Opportunity not found.")
    return item
def _access(db, user, item):
    if not can_access_owner(db, user, item.owner_id): raise HTTPException(403, "You do not have access to this opportunity.")
def _owner_or_error(db, user, owner_id):
    owner_id = owner_id or user.id
    if not can_access_owner(db, user, owner_id): raise HTTPException(403, "You cannot assign this opportunity to that owner.")
    owner = db.get(User, owner_id)
    if not owner or not owner.is_active: raise HTTPException(400, "Opportunity owner must be an active user.")
    return owner
def _relations_or_error(db, user, customer_id, lead_id):
    customer = db.get(Customer, customer_id)
    if not customer: raise HTTPException(400, "Customer not found.")
    if not can_access_owner(db, user, customer.owner_id): raise HTTPException(403, "You do not have access to that customer.")
    if lead_id:
        lead = db.get(Lead, lead_id)
        if not lead: raise HTTPException(400, "Lead not found.")
        if not can_access_owner(db, user, lead.owner_id): raise HTTPException(403, "You do not have access to that lead.")
        if lead.converted_customer_id and lead.converted_customer_id != customer_id: raise HTTPException(400, "Converted lead must use its linked customer.")
def _validate_date(stage, close_date):
    if stage in ACTIVE_STAGES and close_date < date.today(): raise HTTPException(400, "Expected close date cannot be in the past for an active opportunity.")

def list_opportunities(db, *, current_user, search, stage, owner_id, customer_id, page, page_size, sort_by, sort_order):
    stmt = select(Opportunity).options(joinedload(Opportunity.owner), joinedload(Opportunity.customer)); scope = authorized_user_ids(db, current_user)
    if scope is not None: stmt = stmt.where(Opportunity.owner_id.in_(scope))
    if owner_id:
        if not can_access_owner(db, current_user, owner_id): raise HTTPException(403, "You cannot filter by that owner.")
        stmt = stmt.where(Opportunity.owner_id == owner_id)
    if customer_id: stmt = stmt.where(Opportunity.customer_id == customer_id)
    if stage: stmt = stmt.where(Opportunity.stage == stage)
    if search:
        term = f"%{search.strip().lower()}%"; stmt = stmt.where(or_(func.lower(Opportunity.name).like(term), func.lower(Opportunity.opportunity_code).like(term), func.lower(Customer.name).like(term))).join(Customer)
    columns = {"name": Opportunity.name, "stage": Opportunity.stage, "amount": Opportunity.amount, "probability": Opportunity.probability, "expected_close_date": Opportunity.expected_close_date, "created_at": Opportunity.created_at, "opportunity_code": Opportunity.opportunity_code}
    column = columns[sort_by]; stmt = stmt.order_by(column.desc() if sort_order == "desc" else column.asc())
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0; records = db.scalars(stmt.offset((page-1)*page_size).limit(page_size)).unique().all()
    return OpportunityPage.create(items=[_item(x) for x in records], page=page, page_size=page_size, total=total)
def list_owners(db, *, current_user):
    stmt=select(User).where(User.is_active.is_(True)).order_by(User.username); scope=authorized_user_ids(db,current_user)
    if scope is not None: stmt=stmt.where(User.id.in_(scope))
    return [_owner(x) for x in db.scalars(stmt)]
def get_opportunity(db, *, current_user, opportunity_id):
    item=_get(db,opportunity_id); _access(db,current_user,item); return _response(item)
def create_opportunity(db, *, current_user, payload, ip_address):
    owner=_owner_or_error(db,current_user,payload.owner_id); _relations_or_error(db,current_user,payload.customer_id,payload.lead_id); _validate_date("qualification",payload.expected_close_date)
    item=Opportunity(opportunity_code=f"OPP-{uuid4().hex[:12].upper()}",name=payload.name,customer_id=payload.customer_id,lead_id=payload.lead_id,owner_id=owner.id,amount=payload.amount,probability=payload.probability,stage="qualification",status="open",expected_close_date=payload.expected_close_date,source=payload.source,notes=payload.notes); db.add(item); db.flush(); db.refresh(item,attribute_names=["owner","customer"]); write_audit(db,actor_id=current_user.id,action="opportunity_created",entity_name="opportunity",record_id=item.id,new_value=_snapshot(item),ip_address=ip_address); db.commit(); db.refresh(item,attribute_names=["owner","customer"]); return _response(item)
def update_opportunity(db, *, current_user, opportunity_id, payload, ip_address):
    item=_get(db,opportunity_id); _access(db,current_user,item)
    if item.stage in {"won","lost"}: raise HTTPException(400,"Terminal opportunities cannot be edited.")
    changes=payload.model_dump(exclude_unset=True)
    if not changes: return _response(item)
    customer_id=changes.get("customer_id",item.customer_id); lead_id=changes.get("lead_id",item.lead_id); _relations_or_error(db,current_user,customer_id,lead_id)
    if "owner_id" in changes:
        if changes["owner_id"] is None: raise HTTPException(400,"Opportunity owner is required.")
        changes["owner_id"]=_owner_or_error(db,current_user,changes["owner_id"]).id
    _validate_date(item.stage,changes.get("expected_close_date",item.expected_close_date)); old=_snapshot(item)
    for key,value in changes.items(): setattr(item,key,value)
    db.flush(); db.refresh(item,attribute_names=["owner","customer"]); write_audit(db,actor_id=current_user.id,action="opportunity_assigned" if "owner_id" in changes else "opportunity_updated",entity_name="opportunity",record_id=item.id,old_value=old,new_value=_snapshot(item),ip_address=ip_address); db.commit(); db.refresh(item,attribute_names=["owner","customer"]); return _response(item)
def change_stage(db, *, current_user, opportunity_id, payload, ip_address):
    item=_get(db,opportunity_id); _access(db,current_user,item)
    if payload.stage not in STAGE_TRANSITIONS[item.stage]: raise HTTPException(400,f"Cannot transition a {item.stage} opportunity to {payload.stage}.")
    _validate_date(payload.stage,item.expected_close_date); old=_snapshot(item); item.stage=payload.stage; item.status="closed" if payload.stage in {"won","lost"} else "open"; db.flush(); write_audit(db,actor_id=current_user.id,action="opportunity_stage_changed",entity_name="opportunity",record_id=item.id,old_value=old,new_value=_snapshot(item),ip_address=ip_address); db.commit(); db.refresh(item,attribute_names=["owner","customer"]); return _response(item)
def opportunity_history(db, *, current_user, opportunity_id):
    item=_get(db,opportunity_id); _access(db,current_user,item); rows=db.scalars(select(AuditLog).where(AuditLog.entity_name=="opportunity",AuditLog.record_id==str(opportunity_id)).order_by(AuditLog.created_at.desc()))
    return [OpportunityHistoryItem(id=x.id,action=x.action,result=x.result,created_at=x.created_at.isoformat(),actor_id=x.user_id,details=x.details) for x in rows]

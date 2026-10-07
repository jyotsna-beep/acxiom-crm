from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.user import User
from app.policies.authorization import authorized_user_ids, can_access_owner
from app.schemas.customer import CustomerCreate, CustomerHistoryItem, CustomerListItem, CustomerOwnerResponse, CustomerPage, CustomerResponse, CustomerUpdate
from app.services.audit_service import write_audit


def _customer_snapshot(customer: Customer) -> dict[str, str | None]:
    """Keep customer audit metadata useful without storing contact details or notes."""
    return {
        "customer_code": customer.customer_code,
        "name": customer.name,
        "status": customer.status,
        "owner_id": str(customer.owner_id) if customer.owner_id else None,
    }


def _owner_response(owner: User | None) -> CustomerOwnerResponse | None:
    if owner is None:
        return None
    return CustomerOwnerResponse(id=owner.id, username=owner.username, email=owner.email)


def _list_item(customer: Customer) -> CustomerListItem:
    return CustomerListItem(
        id=customer.id,
        customer_code=customer.customer_code,
        name=customer.name,
        email=customer.email,
        phone=customer.phone,
        status=customer.status,
        owner=_owner_response(customer.owner),
    )


def _response(customer: Customer) -> CustomerResponse:
    return CustomerResponse(**_list_item(customer).model_dump(), address=customer.address, notes=customer.notes)


def _customer_or_404(db: Session, customer_id: UUID) -> Customer:
    customer = db.scalar(select(Customer).options(joinedload(Customer.owner)).where(Customer.id == customer_id))
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
    return customer


def _require_customer_access(db: Session, *, current_user: User, customer: Customer) -> None:
    if not can_access_owner(db, current_user, customer.owner_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this customer.")


def _owner_or_error(db: Session, *, current_user: User, requested_owner_id: UUID | None) -> User:
    owner_id = requested_owner_id or current_user.id
    if not can_access_owner(db, current_user, owner_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot assign this customer to that owner.")
    owner = db.get(User, owner_id)
    if owner is None or not owner.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer owner must be an active user.")
    return owner


def _duplicate_or_error(db: Session, *, email: str, phone: str, exclude_id: UUID | None = None) -> None:
    statement = select(Customer.id).where(or_(Customer.email == email, Customer.phone == phone))
    if exclude_id:
        statement = statement.where(Customer.id != exclude_id)
    duplicate_id = db.scalar(statement)
    if duplicate_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A customer with that email or phone already exists.")


def _customer_code() -> str:
    return f"CUST-{uuid4().hex[:12].upper()}"


def list_customers(
    db: Session,
    *,
    current_user: User,
    search: str | None,
    customer_status: str | None,
    owner_id: UUID | None,
    page: int,
    page_size: int,
    sort_by: str,
    sort_order: str,
) -> CustomerPage:
    statement = select(Customer).options(joinedload(Customer.owner))
    scope_ids = authorized_user_ids(db, current_user)
    if scope_ids is not None:
        statement = statement.where(Customer.owner_id.in_(scope_ids))
    if owner_id is not None:
        if not can_access_owner(db, current_user, owner_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot filter by that owner.")
        statement = statement.where(Customer.owner_id == owner_id)
    if customer_status:
        statement = statement.where(Customer.status == customer_status)
    if search:
        term = f"%{search.strip().lower()}%"
        statement = statement.where(
            or_(
                func.lower(Customer.name).like(term),
                func.lower(Customer.email).like(term),
                Customer.phone.like(term),
                func.lower(func.coalesce(Customer.company_name, "")).like(term),
            )
        )
    sort_columns = {"name": Customer.name, "email": Customer.email, "status": Customer.status, "created_at": Customer.created_at, "customer_code": Customer.customer_code}
    sort_column = sort_columns[sort_by]
    statement = statement.order_by(sort_column.desc() if sort_order == "desc" else sort_column.asc())
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    customers = db.scalars(statement.offset((page - 1) * page_size).limit(page_size)).unique().all()
    return CustomerPage.create(items=[_list_item(customer) for customer in customers], page=page, page_size=page_size, total=total)


def list_assignable_owners(db: Session, *, current_user: User) -> list[CustomerOwnerResponse]:
    statement = select(User).where(User.is_active.is_(True)).order_by(User.username.asc(), User.email.asc())
    scope_ids = authorized_user_ids(db, current_user)
    if scope_ids is not None:
        statement = statement.where(User.id.in_(scope_ids))
    return [_owner_response(owner) for owner in db.scalars(statement).all()]


def get_customer(db: Session, *, current_user: User, customer_id: UUID) -> CustomerResponse:
    customer = _customer_or_404(db, customer_id)
    _require_customer_access(db, current_user=current_user, customer=customer)
    return _response(customer)


def create_customer(db: Session, *, current_user: User, payload: CustomerCreate, ip_address: str | None) -> CustomerResponse:
    customer = create_customer_for_conversion(db, current_user=current_user, payload=payload, ip_address=ip_address)
    db.commit()
    db.refresh(customer, attribute_names=["owner"])
    return _response(customer)


def create_customer_for_conversion(db: Session, *, current_user: User, payload: CustomerCreate, ip_address: str | None) -> Customer:
    """Create a customer within the caller's transaction (used by lead conversion)."""
    owner = _owner_or_error(db, current_user=current_user, requested_owner_id=payload.owner_id)
    _duplicate_or_error(db, email=str(payload.email), phone=payload.phone)
    customer = Customer(
        customer_code=_customer_code(),
        name=payload.name,
        email=str(payload.email),
        phone=payload.phone,
        address=payload.address,
        status=payload.status,
        notes=payload.notes,
        owner_id=owner.id,
    )
    db.add(customer)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A customer with that email or phone already exists.") from exc
    db.refresh(customer, attribute_names=["owner"])
    write_audit(db, actor_id=current_user.id, action="customer_created", entity_name="customer", record_id=customer.id, new_value=_customer_snapshot(customer), ip_address=ip_address)
    return customer


def update_customer(db: Session, *, current_user: User, customer_id: UUID, payload: CustomerUpdate, ip_address: str | None) -> CustomerResponse:
    customer = _customer_or_404(db, customer_id)
    _require_customer_access(db, current_user=current_user, customer=customer)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return _response(customer)
    if "owner_id" in updates:
        if updates["owner_id"] is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer owner is required.")
        owner = _owner_or_error(db, current_user=current_user, requested_owner_id=updates.pop("owner_id"))
        updates["owner_id"] = owner.id
    _duplicate_or_error(db, email=updates.get("email", customer.email), phone=updates.get("phone", customer.phone), exclude_id=customer.id)
    old_value = _customer_snapshot(customer)
    for field, value in updates.items():
        setattr(customer, field, value)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A customer with that email or phone already exists.") from exc
    db.refresh(customer, attribute_names=["owner"])
    write_audit(db, actor_id=current_user.id, action="customer_updated", entity_name="customer", record_id=customer.id, old_value=old_value, new_value=_customer_snapshot(customer), ip_address=ip_address)
    db.commit()
    db.refresh(customer, attribute_names=["owner"])
    return _response(customer)


def deactivate_customer(db: Session, *, current_user: User, customer_id: UUID, ip_address: str | None) -> None:
    customer = _customer_or_404(db, customer_id)
    _require_customer_access(db, current_user=current_user, customer=customer)
    if customer.status == "inactive":
        return
    old_value = _customer_snapshot(customer)
    customer.status = "inactive"
    db.flush()
    write_audit(db, actor_id=current_user.id, action="customer_deactivated", entity_name="customer", record_id=customer.id, old_value=old_value, new_value=_customer_snapshot(customer), ip_address=ip_address)
    db.commit()


def customer_history(db: Session, *, current_user: User, customer_id: UUID) -> list[CustomerHistoryItem]:
    customer = _customer_or_404(db, customer_id)
    _require_customer_access(db, current_user=current_user, customer=customer)
    entries = db.scalars(select(AuditLog).where(AuditLog.entity_name == "customer", AuditLog.record_id == str(customer_id)).order_by(AuditLog.created_at.desc())).all()
    return [CustomerHistoryItem(id=entry.id, action=entry.action, result=entry.result, created_at=entry.created_at.isoformat(), actor_id=entry.user_id, details=entry.details) for entry in entries]

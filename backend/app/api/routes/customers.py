from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_csrf
from app.core.database import get_db
from app.models.user import User
from app.schemas.customer import CustomerCreate, CustomerHistoryItem, CustomerOwnerResponse, CustomerPage, CustomerResponse, CustomerUpdate
from app.services.customer_service import create_customer, customer_history, deactivate_customer, get_customer, list_assignable_owners, list_customers, update_customer


router = APIRouter(prefix="/api/customers", tags=["customers"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("", response_model=CustomerPage)
def list_customer_records(
    search: str | None = Query(default=None, max_length=150),
    customer_status: Literal["active", "inactive"] | None = Query(default=None, alias="status"),
    owner_id: UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: Literal["name", "email", "status", "created_at", "customer_code"] = "name",
    sort_order: Literal["asc", "desc"] = "asc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomerPage:
    return list_customers(db, current_user=current_user, search=search, customer_status=customer_status, owner_id=owner_id, page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order)


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer_record(
    payload: CustomerCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_csrf),
) -> CustomerResponse:
    return create_customer(db, current_user=current_user, payload=payload, ip_address=_client_ip(request))


@router.get("/owners", response_model=list[CustomerOwnerResponse])
def get_assignable_owners(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[CustomerOwnerResponse]:
    return list_assignable_owners(db, current_user=current_user)


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer_record(customer_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> CustomerResponse:
    return get_customer(db, current_user=current_user, customer_id=customer_id)


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer_record(
    customer_id: UUID,
    payload: CustomerUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_csrf),
) -> CustomerResponse:
    return update_customer(db, current_user=current_user, customer_id=customer_id, payload=payload, ip_address=_client_ip(request))


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_customer_record(
    customer_id: UUID,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_csrf),
) -> None:
    deactivate_customer(db, current_user=current_user, customer_id=customer_id, ip_address=_client_ip(request))


@router.get("/{customer_id}/history", response_model=list[CustomerHistoryItem])
def get_customer_history(customer_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[CustomerHistoryItem]:
    return customer_history(db, current_user=current_user, customer_id=customer_id)

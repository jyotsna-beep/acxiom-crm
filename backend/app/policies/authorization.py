from enum import StrEnum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class RoleName(StrEnum):
    ADMIN = "Admin"
    MANAGER = "Manager"
    SALES_EXECUTIVE = "Sales Executive"


class ScopeMode(StrEnum):
    ALL = "all"
    TEAM = "team"
    OWN = "own"


def role_name(user: User) -> str:
    return user.role.name


def has_any_role(user: User, *allowed_roles: RoleName) -> bool:
    return role_name(user) in {role.value for role in allowed_roles}


def scope_mode(user: User) -> ScopeMode:
    if has_any_role(user, RoleName.ADMIN):
        return ScopeMode.ALL
    if has_any_role(user, RoleName.MANAGER):
        return ScopeMode.TEAM
    return ScopeMode.OWN


def authorized_user_ids(db: Session, user: User) -> set[UUID] | None:
    """Return users whose owned/assigned records are in scope; None means all users."""
    mode = scope_mode(user)
    if mode is ScopeMode.ALL:
        return None
    if mode is ScopeMode.OWN:
        return {user.id}
    report_ids = set(db.scalars(select(User.id).where(User.manager_id == user.id)).all())
    return {user.id, *report_ids}


def can_access_owner(db: Session, user: User, owner_id: UUID | None) -> bool:
    if owner_id is None:
        return scope_mode(user) is ScopeMode.ALL
    permitted_user_ids = authorized_user_ids(db, user)
    return permitted_user_ids is None or owner_id in permitted_user_ids

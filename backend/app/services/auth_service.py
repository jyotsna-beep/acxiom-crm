from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.security import PasswordPolicyError, hash_password, verify_password
from app.models.audit_log import AuditLog
from app.models.role import Role
from app.models.user import User
from app.policies.authorization import RoleName
from app.schemas.auth import RegisterRequest


class AuthenticationFailed(Exception):
    pass


class AccountLocked(Exception):
    pass


def _audit(
    db: Session,
    *,
    action: str,
    result: str,
    user_id: UUID | None = None,
    record_id: UUID | None = None,
    ip_address: str | None = None,
    details: str | None = None,
) -> None:
    """Write security audit metadata only; never include credentials or tokens."""
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            entity_name="authentication",
            record_id=str(record_id) if record_id else None,
            result=result,
            ip_address=ip_address,
            details=details,
        )
    )


def authenticate_user(db: Session, *, identity: str, password: str, ip_address: str | None) -> User:
    """Authenticate a user while applying lockout policy and durable audit events."""
    settings = get_settings()
    normalized_identity = identity.strip().lower()
    user = db.scalar(
        select(User)
        .options(joinedload(User.role))
        .where(or_(func.lower(User.email) == normalized_identity, func.lower(User.username) == normalized_identity))
    )
    now = datetime.now(UTC)

    if user is None:
        _audit(db, action="login_failed", result="failure", ip_address=ip_address, details="Unknown account")
        db.commit()
        raise AuthenticationFailed

    if not user.is_active:
        _audit(db, action="login_failed", result="failure", user_id=user.id, record_id=user.id, ip_address=ip_address, details="Inactive account")
        db.commit()
        raise AuthenticationFailed

    if user.lockout_until and user.lockout_until > now:
        _audit(db, action="login_failed", result="failure", user_id=user.id, record_id=user.id, ip_address=ip_address, details="Locked account")
        db.commit()
        raise AccountLocked

    if not verify_password(password, user.password_hash):
        user.failed_login_count += 1
        _audit(db, action="login_failed", result="failure", user_id=user.id, record_id=user.id, ip_address=ip_address, details="Invalid credentials")
        if user.failed_login_count >= settings.lockout_max_attempts:
            user.lockout_until = now + timedelta(minutes=settings.lockout_duration_minutes)
            _audit(db, action="account_locked", result="success", user_id=user.id, record_id=user.id, ip_address=ip_address)
        db.commit()
        raise AuthenticationFailed

    user.failed_login_count = 0
    user.lockout_until = None
    _audit(db, action="login_success", result="success", user_id=user.id, record_id=user.id, ip_address=ip_address)
    db.commit()
    db.refresh(user)
    return user


def logout_user(db: Session, *, user: User, ip_address: str | None) -> None:
    """Invalidate all outstanding tokens for the user and audit the logout."""
    user.token_version += 1
    _audit(db, action="logout", result="success", user_id=user.id, record_id=user.id, ip_address=ip_address)
    db.commit()


def register_sales_executive(db: Session, *, request: RegisterRequest, ip_address: str | None) -> User:
    """Create an inactive Sales Executive account without accepting a client-supplied role."""
    email = str(request.email).lower()
    username = request.username.strip() if request.username else None
    duplicate = db.scalar(
        select(User.id).where(or_(func.lower(User.email) == email, User.username == username if username else False))
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with those details already exists.")

    role = db.scalar(select(Role).where(Role.name == RoleName.SALES_EXECUTIVE.value))
    if role is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Registration is temporarily unavailable.")
    try:
        password_hash = hash_password(request.password)
    except PasswordPolicyError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    user = User(
        name=request.name.strip(),
        email=email,
        username=username,
        password_hash=password_hash,
        role_id=role.id,
        is_active=False,
    )
    db.add(user)
    db.flush()
    _audit(db, action="registration_requested", result="success", record_id=user.id, ip_address=ip_address)
    db.commit()
    return user

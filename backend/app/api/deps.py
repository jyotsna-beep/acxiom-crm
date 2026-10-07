from collections.abc import Callable
import secrets
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.audit_log import AuditLog
from app.models.user import User
from app.policies.authorization import RoleName, has_any_role


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required.")


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    settings = get_settings()
    token = request.cookies.get(settings.auth_cookie_name)
    if not token:
        raise _unauthorized()
    try:
        payload = decode_access_token(token)
        user_id = UUID(payload["sub"])
        token_version = int(payload["token_version"])
    except (KeyError, TypeError, ValueError):
        raise _unauthorized() from None

    user = db.scalar(select(User).options(joinedload(User.role)).where(User.id == user_id))
    if user is None or not user.is_active or user.token_version != token_version:
        raise _unauthorized()
    return user


def require_roles(*allowed_roles: RoleName) -> Callable:
    def dependency(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if not has_any_role(current_user, *allowed_roles):
            db.add(
                AuditLog(
                    user_id=current_user.id,
                    action="authorization_denied",
                    entity_name="authorization",
                    record_id=str(current_user.id),
                    result="failure",
                    ip_address=request.client.host if request.client else None,
                    details="Insufficient role privileges",
                )
            )
            db.commit()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this resource.")
        return current_user

    return dependency


def _validate_csrf(request: Request) -> None:
    settings = get_settings()
    csrf_header = request.headers.get("X-CSRF-Token")
    csrf_cookie = request.cookies.get(settings.csrf_cookie_name)
    if not csrf_header or not csrf_cookie or not secrets.compare_digest(csrf_header, csrf_cookie):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token.")


def require_public_csrf(request: Request) -> None:
    _validate_csrf(request)


def require_csrf(request: Request, current_user: User = Depends(get_current_user)) -> User:
    _validate_csrf(request)
    settings = get_settings()
    token = request.cookies.get(settings.auth_cookie_name)
    try:
        payload = decode_access_token(token or "")
        if not secrets.compare_digest(payload["csrf"], request.headers["X-CSRF-Token"]):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token.") from None
    return current_user

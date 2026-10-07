from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_csrf, require_public_csrf
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token, generate_csrf_token
from app.models.user import User
from app.schemas.auth import AuthResponse, CurrentUserResponse, LoginRequest, RegistrationResponse, RegisterRequest
from app.services.auth_service import AccountLocked, AuthenticationFailed, authenticate_user, logout_user, register_sales_executive


router = APIRouter(prefix="/api/auth", tags=["authentication"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _set_csrf_cookie(response: Response, csrf_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )


def _set_auth_cookies(response: Response, user: User) -> None:
    settings = get_settings()
    csrf_token = generate_csrf_token()
    token = create_access_token(user_id=user.id, token_version=user.token_version, csrf_token=csrf_token)
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    _set_csrf_cookie(response, csrf_token)


def _clear_auth_cookies(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(settings.auth_cookie_name, path="/", secure=settings.cookie_secure, samesite=settings.cookie_samesite)
    response.delete_cookie(settings.csrf_cookie_name, path="/", secure=settings.cookie_secure, samesite=settings.cookie_samesite)


def _user_response(user: User) -> CurrentUserResponse:
    return CurrentUserResponse(id=user.id, email=user.email, username=user.username, role=user.role.name, is_active=user.is_active)


@router.get("/csrf", status_code=status.HTTP_204_NO_CONTENT)
def issue_public_csrf_token(response: Response) -> None:
    _set_csrf_cookie(response, generate_csrf_token())


@router.post("/register", status_code=status.HTTP_202_ACCEPTED, response_model=RegistrationResponse)
def register(request: RegisterRequest, http_request: Request, db: Session = Depends(get_db), _: None = Depends(require_public_csrf)) -> RegistrationResponse:
    register_sales_executive(db, request=request, ip_address=_client_ip(http_request))
    return RegistrationResponse(message="Registration received. An administrator must activate the account.")


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response, request: Request, db: Session = Depends(get_db), _: None = Depends(require_public_csrf)) -> AuthResponse:
    try:
        user = authenticate_user(db, identity=payload.identity, password=payload.password, ip_address=_client_ip(request))
    except AccountLocked as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Account is temporarily locked.") from exc
    except AuthenticationFailed as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.") from exc
    _set_auth_cookies(response, user)
    return AuthResponse(user=_user_response(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_csrf)) -> None:
    logout_user(db, user=current_user, ip_address=_client_ip(request))
    _clear_auth_cookies(response)


@router.get("/me", response_model=CurrentUserResponse)
def current_user(current_user: User = Depends(get_current_user)) -> CurrentUserResponse:
    return _user_response(current_user)

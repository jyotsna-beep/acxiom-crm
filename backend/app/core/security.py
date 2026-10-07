from datetime import UTC, datetime, timedelta
import secrets
from typing import Any
from uuid import UUID

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import get_settings


password_hasher = PasswordHash.recommended()


class PasswordPolicyError(ValueError):
    """Raised when a password does not meet the configured baseline policy."""


def validate_password_policy(password: str) -> None:
    """Enforce the assignment's minimum-length and character-class policy."""
    if len(password) < 8:
        raise PasswordPolicyError("Password must be at least 8 characters long.")
    if not any(character.islower() for character in password):
        raise PasswordPolicyError("Password must include a lowercase letter.")
    if not any(character.isupper() for character in password):
        raise PasswordPolicyError("Password must include an uppercase letter.")
    if not any(character.isdigit() for character in password):
        raise PasswordPolicyError("Password must include a number.")
    if not any(not character.isalnum() for character in password):
        raise PasswordPolicyError("Password must include a special character.")


def hash_password(password: str) -> str:
    validate_password_policy(password)
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def create_access_token(*, user_id: UUID, token_version: int, csrf_token: str) -> str:
    settings = get_settings()
    issued_at = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "token_version": token_version,
        "csrf": csrf_token,
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.auth_secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.auth_secret_key, algorithms=["HS256"])
    except InvalidTokenError as exc:
        raise ValueError("Invalid authentication token.") from exc

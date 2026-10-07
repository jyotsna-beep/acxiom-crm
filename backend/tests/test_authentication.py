import os
import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("AUTH_SECRET_KEY", "unit-test-secret-not-for-production-123456")
os.environ.setdefault("LOCKOUT_MAX_ATTEMPTS", "2")
os.environ.setdefault("LOCKOUT_DURATION_MINUTES", "15")

from fastapi import HTTPException

from app.api.deps import get_current_user, require_roles
from app.core.config import get_settings
from app.core.security import PasswordPolicyError, hash_password, validate_password_policy
from app.models.user import User
from app.models.role import Role
from app.policies.authorization import RoleName, ScopeMode, authorized_user_ids, scope_mode
from app.schemas.auth import CurrentUserResponse
from app.services.auth_service import AccountLocked, AuthenticationFailed, authenticate_user


class FakeScalars:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class FakeSession:
    def __init__(self, user=None, report_ids=None):
        self.user = user
        self.report_ids = report_ids or []
        self.audit_entries = []
        self.commits = 0

    def scalar(self, _statement):
        return self.user

    def scalars(self, _statement):
        return FakeScalars(self.report_ids)

    def add(self, item):
        self.audit_entries.append(item)

    def commit(self):
        self.commits += 1

    def refresh(self, _user):
        pass


def make_user(*, role="Sales Executive", active=True, failed_attempts=0):
    user = User(
        id=uuid4(),
        name="Test User",
        email="test@example.com",
        username="testuser",
        password_hash=hash_password("Valid#Password1"),
        role_id=uuid4(),
        is_active=active,
        failed_login_count=failed_attempts,
        token_version=0,
    )
    user.role = Role(id=uuid4(), name=role)
    return user


class PasswordPolicyTests(unittest.TestCase):
    def test_rejects_password_without_required_classes(self):
        with self.assertRaises(PasswordPolicyError):
            validate_password_policy("alllowercase1")

    def test_hash_never_equals_plaintext(self):
        password_hash = hash_password("Valid#Password1")
        self.assertNotEqual(password_hash, "Valid#Password1")


class AuthenticationServiceTests(unittest.TestCase):
    def setUp(self):
        get_settings.cache_clear()

    def test_valid_login_resets_failed_attempt_state(self):
        user = make_user(failed_attempts=1)
        user.lockout_until = datetime.now(UTC) - timedelta(minutes=1)
        db = FakeSession(user)

        authenticated = authenticate_user(db, identity="TEST@EXAMPLE.COM", password="Valid#Password1", ip_address="127.0.0.1")

        self.assertIs(authenticated, user)
        self.assertEqual(user.failed_login_count, 0)
        self.assertIsNone(user.lockout_until)
        self.assertEqual(db.audit_entries[-1].action, "login_success")

    def test_invalid_password_tracks_failure_and_locks_account(self):
        user = make_user(failed_attempts=1)
        db = FakeSession(user)

        with self.assertRaises(AuthenticationFailed):
            authenticate_user(db, identity="test@example.com", password="Wrong#Password1", ip_address=None)

        self.assertEqual(user.failed_login_count, 2)
        self.assertIsNotNone(user.lockout_until)
        self.assertEqual(db.audit_entries[-1].action, "account_locked")

    def test_locked_account_rejects_login(self):
        user = make_user()
        user.lockout_until = datetime.now(UTC) + timedelta(minutes=5)

        with self.assertRaises(AccountLocked):
            authenticate_user(FakeSession(user), identity="test@example.com", password="Valid#Password1", ip_address=None)

    def test_inactive_account_rejects_login(self):
        with self.assertRaises(AuthenticationFailed):
            authenticate_user(FakeSession(make_user(active=False)), identity="test@example.com", password="Valid#Password1", ip_address=None)


class AuthorizationPolicyTests(unittest.TestCase):
    def test_admin_has_full_scope(self):
        self.assertEqual(scope_mode(make_user(role="Admin")), ScopeMode.ALL)

    def test_manager_has_direct_team_scope(self):
        manager = make_user(role="Manager")
        report_id = uuid4()
        self.assertEqual(scope_mode(manager), ScopeMode.TEAM)
        self.assertEqual(authorized_user_ids(FakeSession(report_ids=[report_id]), manager), {manager.id, report_id})

    def test_sales_executive_has_own_scope(self):
        self.assertEqual(scope_mode(make_user(role="Sales Executive")), ScopeMode.OWN)

    def test_unauthenticated_request_is_rejected(self):
        with self.assertRaises(HTTPException) as error:
            get_current_user(SimpleNamespace(cookies={}), FakeSession())
        self.assertEqual(error.exception.status_code, 401)

    def test_forbidden_role_is_rejected(self):
        dependency = require_roles(RoleName.ADMIN)
        db = FakeSession()
        with self.assertRaises(HTTPException) as error:
            dependency(SimpleNamespace(client=SimpleNamespace(host="127.0.0.1")), make_user(role="Sales Executive"), db)
        self.assertEqual(error.exception.status_code, 403)
        self.assertEqual(db.audit_entries[-1].action, "authorization_denied")


class ResponseSafetyTests(unittest.TestCase):
    def test_password_hash_is_not_in_current_user_response(self):
        user = make_user()
        response = CurrentUserResponse(id=user.id, email=user.email, username=user.username, role=user.role.name, is_active=user.is_active)
        self.assertNotIn("password_hash", response.model_dump())


if __name__ == "__main__":
    unittest.main()

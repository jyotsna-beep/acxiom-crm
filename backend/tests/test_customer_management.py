import os
from pathlib import Path
import unittest
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, event, select
from sqlalchemy.orm import Session, sessionmaker


from test_support import TEST_DATABASE

from app.api.deps import get_db
from app.core.config import get_settings
from app.core.security import hash_password
from app.main import app
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.role import Role
from app.models.user import User


class CustomerApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        get_settings.cache_clear()
        if TEST_DATABASE.exists():
            TEST_DATABASE.unlink()
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        command.upgrade(config, "head")
        cls.engine = create_engine(os.environ["DATABASE_URL"], connect_args={"check_same_thread": False})

        @event.listens_for(cls.engine, "connect")
        def enable_foreign_keys(dbapi_connection, _connection_record):
            dbapi_connection.execute("PRAGMA foreign_keys=ON")

        cls.Session = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False, expire_on_commit=False)

        def override_get_db():
            db = cls.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        cls.engine.dispose()
        if TEST_DATABASE.exists():
            TEST_DATABASE.unlink()

    def setUp(self):
        with self.Session.begin() as db:
            db.execute(delete(AuditLog))
            db.execute(delete(Customer))
            db.execute(delete(User))
            roles = {role.name: role for role in db.scalars(select(Role)).all()}
            self.admin = self._user("Admin", roles["Admin"].id)
            self.manager = self._user("Manager", roles["Manager"].id)
            self.sales_one = self._user("Sales Executive", roles["Sales Executive"].id, manager_id=self.manager.id)
            self.sales_two = self._user("Sales Executive", roles["Sales Executive"].id)
            db.add_all([self.admin, self.manager, self.sales_one, self.sales_two])
        self.client.cookies.clear()

    @staticmethod
    def _user(role_name, role_id, manager_id=None):
        suffix = uuid4().hex[:8]
        return User(
            id=uuid4(),
            name=f"{role_name} {suffix}",
            email=f"{role_name.lower().replace(' ', '')}-{suffix}@example.com",
            username=f"{role_name.lower().replace(' ', '')}-{suffix}",
            password_hash=hash_password("Valid#Password1"),
            role_id=role_id,
            manager_id=manager_id,
            is_active=True,
        )

    def login(self, user):
        self.client.cookies.clear()
        self.assertEqual(self.client.get("/api/auth/csrf").status_code, 204)
        response = self.client.post(
            "/api/auth/login",
            json={"identity": user.username, "password": "Valid#Password1"},
            headers={"X-CSRF-Token": self.client.cookies.get("acxiomcrm_csrf")},
        )
        self.assertEqual(response.status_code, 200)
        return response

    @staticmethod
    def payload(**overrides):
        phone_suffix = f"{uuid4().int % 10**7:07d}"
        base = {
            "name": "Acme Corporation",
            "email": f"customer-{uuid4().hex[:8]}@example.com",
            "phone": f"+1 415 {phone_suffix[:3]}-{phone_suffix[3:]}",
            "address": "1 Main Street",
            "status": "active",
            "notes": "Prospective strategic customer.",
        }
        base.update(overrides)
        return base

    def create_as(self, user, **overrides):
        self.login(user)
        return self.client.post("/api/customers", json=self.payload(**overrides), headers={"X-CSRF-Token": self.client.cookies.get("acxiomcrm_csrf")})

    def test_admin_can_create_customer_and_sensitive_fields_are_excluded(self):
        response = self.create_as(self.admin)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "active")
        self.assertNotIn("password_hash", response.json())

    def test_manager_can_access_direct_report_customer(self):
        response = self.create_as(self.admin, owner_id=str(self.sales_one.id))
        customer_id = response.json()["id"]
        self.login(self.manager)
        self.assertEqual(self.client.get(f"/api/customers/{customer_id}").status_code, 200)

    def test_sales_executive_can_only_access_own_customer(self):
        own_customer = self.create_as(self.sales_one).json()
        other_customer = self.create_as(self.sales_two).json()
        self.login(self.sales_one)
        self.assertEqual(self.client.get(f"/api/customers/{own_customer['id']}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/customers/{other_customer['id']}").status_code, 403)

    def test_unauthenticated_customer_request_is_rejected(self):
        self.assertEqual(self.client.get("/api/customers").status_code, 401)

    def test_invalid_email_phone_and_status_are_rejected(self):
        self.login(self.admin)
        headers = {"X-CSRF-Token": self.client.cookies.get("acxiomcrm_csrf")}
        self.assertEqual(self.client.post("/api/customers", json=self.payload(email="invalid"), headers=headers).status_code, 422)
        self.assertEqual(self.client.post("/api/customers", json=self.payload(phone="not a phone"), headers=headers).status_code, 422)
        self.assertEqual(self.client.post("/api/customers", json=self.payload(status="unknown"), headers=headers).status_code, 422)

    def test_duplicate_email_and_phone_are_rejected(self):
        first = self.create_as(self.admin).json()
        duplicate_email = self.create_as(self.admin, email=first["email"], phone="+1 415 555 0999")
        duplicate_phone = self.create_as(self.admin, email=f"new-{uuid4().hex[:8]}@example.com", phone=first["phone"])
        self.assertEqual(duplicate_email.status_code, 409)
        self.assertEqual(duplicate_phone.status_code, 409)

    def test_invalid_owner_is_rejected(self):
        response = self.create_as(self.admin, owner_id=str(uuid4()))
        self.assertEqual(response.status_code, 400)

    def test_sales_executive_cannot_assign_other_owner(self):
        response = self.create_as(self.sales_one, owner_id=str(self.sales_two.id))
        self.assertEqual(response.status_code, 403)

    def test_update_and_deactivation_generate_audit_history(self):
        customer = self.create_as(self.admin).json()
        self.login(self.admin)
        headers = {"X-CSRF-Token": self.client.cookies.get("acxiomcrm_csrf")}
        update = self.client.put(f"/api/customers/{customer['id']}", json={"name": "Updated Acme"}, headers=headers)
        deactivate = self.client.delete(f"/api/customers/{customer['id']}", headers=headers)
        details = self.client.get(f"/api/customers/{customer['id']}")
        history = self.client.get(f"/api/customers/{customer['id']}/history")
        self.assertEqual(update.status_code, 200)
        self.assertEqual(deactivate.status_code, 204)
        self.assertEqual(details.json()["status"], "inactive")
        self.assertEqual({entry["action"] for entry in history.json()}, {"customer_created", "customer_updated", "customer_deactivated"})

    def test_pagination_search_and_status_filter_are_server_side(self):
        self.create_as(self.admin, name="Alpha Client", email="alpha@example.com", phone="+1 415 555 0111")
        self.create_as(self.admin, name="Beta Client", email="beta@example.com", phone="+1 415 555 0222")
        self.login(self.admin)
        page = self.client.get("/api/customers", params={"page": 1, "page_size": 1, "sort_by": "name"}).json()
        search = self.client.get("/api/customers", params={"search": "beta", "status": "active"}).json()
        self.assertEqual(len(page["items"]), 1)
        self.assertGreaterEqual(page["total"], 2)
        self.assertEqual(search["total"], 1)
        self.assertEqual(search["items"][0]["name"], "Beta Client")


if __name__ == "__main__":
    unittest.main()

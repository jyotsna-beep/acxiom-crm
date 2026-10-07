import os
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, event, select
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker

TEST_DATABASE = Path(tempfile.gettempdir()) / "acxiomcrm-lead-tests.db"
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{TEST_DATABASE.as_posix()}"
os.environ["AUTH_SECRET_KEY"] = "unit-test-secret-not-for-production-123456"
os.environ["COOKIE_SECURE"] = "false"
from app.api.deps import get_db
from app.core.config import get_settings
from app.core.security import hash_password
from app.main import app
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.lead import Lead
from app.models.role import Role
from app.models.user import User


class LeadApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        get_settings.cache_clear()
        if TEST_DATABASE.exists(): TEST_DATABASE.unlink()
        command.upgrade(Config(str(Path(__file__).resolve().parents[1] / "alembic.ini")), "head")
        cls.engine = create_engine(os.environ["DATABASE_URL"], connect_args={"check_same_thread": False})
        event.listen(cls.engine, "connect", lambda conn, _: conn.execute("PRAGMA foreign_keys=ON"))
        cls.Session = sessionmaker(bind=cls.engine, expire_on_commit=False)
        def override():
            db = cls.Session()
            try: yield db
            finally: db.close()
        app.dependency_overrides[get_db] = override; cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear(); cls.engine.dispose()
        if TEST_DATABASE.exists(): TEST_DATABASE.unlink()

    def setUp(self):
        with self.Session.begin() as db:
            db.execute(delete(AuditLog)); db.execute(delete(Lead)); db.execute(delete(Customer)); db.execute(delete(User))
            roles = {role.name: role.id for role in db.scalars(select(Role))}
            self.admin = self.user("admin", roles["Admin"]); self.manager = self.user("manager", roles["Manager"])
            self.sales = self.user("sales", roles["Sales Executive"], self.manager.id); self.other = self.user("other", roles["Sales Executive"])
            db.add_all([self.admin, self.manager, self.sales, self.other])
        self.client.cookies.clear()

    @staticmethod
    def user(prefix, role_id, manager_id=None):
        suffix = uuid4().hex[:8]
        return User(id=uuid4(), name=prefix, email=f"{prefix}{suffix}@example.com", username=f"{prefix}{suffix}", password_hash=hash_password("Valid#Password1"), role_id=role_id, manager_id=manager_id, is_active=True)

    def login(self, user):
        self.client.cookies.clear(); self.client.get("/api/auth/csrf")
        response = self.client.post("/api/auth/login", json={"identity": user.username, "password": "Valid#Password1"}, headers={"X-CSRF-Token": self.client.cookies.get("acxiomcrm_csrf")})
        self.assertEqual(response.status_code, 200)

    def payload(self, **changes):
        data = {"name": "Qualified Prospect", "email": f"lead{uuid4().hex[:8]}@example.com", "phone": "+1 415 555 0123", "source": "Website", "priority": "high", "notes": "Safe note"}; data.update(changes); return data

    def create(self, user, **changes):
        self.login(user); return self.client.post("/api/leads", json=self.payload(**changes), headers={"X-CSRF-Token": self.client.cookies.get("acxiomcrm_csrf")})

    def test_create_scope_and_unauthenticated_access(self):
        lead = self.create(self.sales).json(); self.assertEqual(lead["status"], "new")
        other = self.create(self.other).json(); self.login(self.sales)
        self.assertEqual(self.client.get(f"/api/leads/{lead['id']}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/leads/{other['id']}").status_code, 403)
        self.client.cookies.clear(); self.assertEqual(self.client.get("/api/leads").status_code, 401)

    def test_validation_assignment_search_and_pagination(self):
        self.login(self.admin); h = {"X-CSRF-Token": self.client.cookies.get("acxiomcrm_csrf")}
        self.assertEqual(self.client.post("/api/leads", json=self.payload(email="bad"), headers=h).status_code, 422)
        self.assertEqual(self.client.post("/api/leads", json=self.payload(phone="bad"), headers=h).status_code, 422)
        self.assertEqual(self.client.post("/api/leads", json=self.payload(priority="urgent"), headers=h).status_code, 422)
        self.assertEqual(self.client.post("/api/leads", json=self.payload(owner_id=str(uuid4())), headers=h).status_code, 400)
        self.create(self.admin, name="Alpha Prospect"); self.create(self.admin, name="Beta Prospect")
        result = self.client.get("/api/leads", params={"search": "beta", "page_size": 1}).json()
        self.assertEqual(result["total"], 1); self.assertEqual(result["items"][0]["name"], "Beta Prospect")

    def test_transition_conversion_duplicate_and_audit(self):
        lead = self.create(self.admin).json(); self.login(self.admin); h = {"X-CSRF-Token": self.client.cookies.get("acxiomcrm_csrf")}
        self.assertEqual(self.client.post(f"/api/leads/{lead['id']}/status", json={"status": "qualified"}, headers=h).status_code, 200)
        converted = self.client.post(f"/api/leads/{lead['id']}/convert", headers=h)
        self.assertEqual(converted.status_code, 200); self.assertEqual(self.client.post(f"/api/leads/{lead['id']}/convert", headers=h).status_code, 409)
        history = self.client.get(f"/api/leads/{lead['id']}/history").json(); self.assertIn("lead_converted", {entry["action"] for entry in history})
        duplicate = self.create(self.admin, email=lead["email"], phone=lead["phone"]).json()
        self.login(self.admin); h = {"X-CSRF-Token": self.client.cookies.get("acxiomcrm_csrf")}
        self.client.post(f"/api/leads/{duplicate['id']}/status", json={"status": "qualified"}, headers=h)
        self.assertEqual(self.client.post(f"/api/leads/{duplicate['id']}/convert", headers=h).status_code, 409)

    def test_invalid_transition_and_manager_team_access(self):
        lead = self.create(self.sales).json(); self.login(self.manager); self.assertEqual(self.client.get(f"/api/leads/{lead['id']}").status_code, 200)
        self.login(self.sales); h = {"X-CSRF-Token": self.client.cookies.get("acxiomcrm_csrf")}
        self.assertEqual(self.client.post(f"/api/leads/{lead['id']}/status", json={"status": "lost"}, headers=h).status_code, 200)
        self.assertEqual(self.client.post(f"/api/leads/{lead['id']}/status", json={"status": "contacted"}, headers=h).status_code, 400)

    def test_invalid_status_input_is_rejected(self):
        lead = self.create(self.admin).json()
        self.login(self.admin)
        response = self.client.post(
            f"/api/leads/{lead['id']}/status",
            json={"status": "not-a-lead-status"},
            headers={"X-CSRF-Token": self.client.cookies.get("acxiomcrm_csrf")},
        )
        self.assertEqual(response.status_code, 422)

    def test_update_returns_and_persists_editable_fields(self):
        lead = self.create(self.admin).json()
        self.login(self.admin)
        headers = {"X-CSRF-Token": self.client.cookies.get("acxiomcrm_csrf")}
        response = self.client.put(
            f"/api/leads/{lead['id']}",
            json={"name": "Updated Prospect", "source": "Referral", "priority": "low", "notes": "Updated note"},
            headers=headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Updated Prospect")
        self.assertEqual(response.json()["priority"], "low")
        retrieved = self.client.get(f"/api/leads/{lead['id']}")
        self.assertEqual(retrieved.status_code, 200)
        self.assertEqual(retrieved.json()["source"], "Referral")
        self.assertEqual(retrieved.json()["notes"], "Updated note")

    def test_status_priority_and_owner_filters_are_server_side(self):
        new_low = self.create(self.admin, name="New Low", priority="low").json()
        contacted_high = self.create(self.admin, name="Contacted High", priority="high", owner_id=str(self.sales.id)).json()
        self.login(self.admin)
        headers = {"X-CSRF-Token": self.client.cookies.get("acxiomcrm_csrf")}
        self.assertEqual(self.client.post(f"/api/leads/{contacted_high['id']}/status", json={"status": "contacted"}, headers=headers).status_code, 200)
        status_results = self.client.get("/api/leads", params={"status": "contacted"}).json()["items"]
        priority_results = self.client.get("/api/leads", params={"priority": "low"}).json()["items"]
        owner_results = self.client.get("/api/leads", params={"owner_id": str(self.sales.id)}).json()["items"]
        self.assertEqual({lead["id"] for lead in status_results}, {contacted_high["id"]})
        self.assertEqual({lead["id"] for lead in priority_results}, {new_low["id"]})
        self.assertEqual({lead["id"] for lead in owner_results}, {contacted_high["id"]})

    def test_pagination_has_distinct_pages_and_consistent_metadata(self):
        for number in range(3):
            self.create(self.admin, name=f"Paged Prospect {number}")
        self.login(self.admin)
        first = self.client.get("/api/leads", params={"page": 1, "page_size": 2, "sort_by": "lead_code"}).json()
        second = self.client.get("/api/leads", params={"page": 2, "page_size": 2, "sort_by": "lead_code"}).json()
        self.assertEqual(first["total"], 3)
        self.assertEqual(first["total_pages"], 2)
        self.assertEqual(len(first["items"]), 2)
        self.assertEqual(len(second["items"]), 1)
        self.assertTrue({lead["id"] for lead in first["items"]}.isdisjoint({lead["id"] for lead in second["items"]}))

    def test_status_change_writes_audit_record(self):
        lead = self.create(self.admin).json()
        self.login(self.admin)
        headers = {"X-CSRF-Token": self.client.cookies.get("acxiomcrm_csrf")}
        self.assertEqual(self.client.post(f"/api/leads/{lead['id']}/status", json={"status": "contacted"}, headers=headers).status_code, 200)
        history = self.client.get(f"/api/leads/{lead['id']}/history").json()
        self.assertIn("lead_status_changed", {entry["action"] for entry in history})

    def test_other_sales_executive_cannot_convert_and_creates_no_customer(self):
        lead = self.create(self.sales).json()
        self.login(self.sales)
        headers = {"X-CSRF-Token": self.client.cookies.get("acxiomcrm_csrf")}
        self.assertEqual(self.client.post(f"/api/leads/{lead['id']}/status", json={"status": "qualified"}, headers=headers).status_code, 200)
        with self.Session() as db:
            before = db.scalar(select(func.count()).select_from(Customer))
        self.login(self.other)
        response = self.client.post(f"/api/leads/{lead['id']}/convert", headers={"X-CSRF-Token": self.client.cookies.get("acxiomcrm_csrf")})
        self.assertEqual(response.status_code, 403)
        self.login(self.admin)
        lead_after = self.client.get(f"/api/leads/{lead['id']}").json()
        with self.Session() as db:
            after = db.scalar(select(func.count()).select_from(Customer))
        self.assertEqual(lead_after["status"], "qualified")
        self.assertIsNone(lead_after["converted_customer_id"])
        self.assertEqual(after, before)

    def test_conversion_creates_and_links_customer(self):
        lead = self.create(self.admin, name="Conversion Prospect", email="convert@example.com", phone="+1 415 555 0444").json()
        self.login(self.admin)
        headers = {"X-CSRF-Token": self.client.cookies.get("acxiomcrm_csrf")}
        self.assertEqual(self.client.post(f"/api/leads/{lead['id']}/status", json={"status": "qualified"}, headers=headers).status_code, 200)
        conversion = self.client.post(f"/api/leads/{lead['id']}/convert", headers=headers)
        self.assertEqual(conversion.status_code, 200)
        customer_id = conversion.json()["customer_id"]
        customer = self.client.get(f"/api/customers/{customer_id}")
        self.assertEqual(customer.status_code, 200)
        self.assertEqual(customer.json()["name"], lead["name"])
        self.assertEqual(customer.json()["email"], lead["email"])
        self.assertEqual(customer.json()["phone"], lead["phone"])
        lead_after = self.client.get(f"/api/leads/{lead['id']}").json()
        self.assertEqual(lead_after["status"], "converted")
        self.assertEqual(lead_after["converted_customer_id"], customer_id)

import os
from datetime import date, timedelta
from pathlib import Path
import unittest
from uuid import uuid4
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, event, select
from sqlalchemy.orm import sessionmaker

from test_support import TEST_DATABASE
from app.api.deps import get_db
from app.core.config import get_settings
from app.core.security import hash_password
from app.main import app
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.lead import Lead
from app.models.opportunity import Opportunity
from app.models.role import Role
from app.models.user import User

class OpportunityApiTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  get_settings.cache_clear()
  if TEST_DATABASE.exists(): TEST_DATABASE.unlink()
  command.upgrade(Config(str(Path(__file__).resolve().parents[1]/"alembic.ini")),"head")
  cls.engine=create_engine(os.environ["DATABASE_URL"],connect_args={"check_same_thread":False}); event.listen(cls.engine,"connect",lambda c,_:c.execute("PRAGMA foreign_keys=ON")); cls.Session=sessionmaker(bind=cls.engine,expire_on_commit=False)
  def override():
   db=cls.Session()
   try: yield db
   finally: db.close()
  app.dependency_overrides[get_db]=override; cls.client=TestClient(app)
 @classmethod
 def tearDownClass(cls):
  app.dependency_overrides.clear(); cls.engine.dispose()
  if TEST_DATABASE.exists(): TEST_DATABASE.unlink()
 def setUp(self):
  with self.Session.begin() as db:
   db.execute(delete(AuditLog)); db.execute(delete(Opportunity)); db.execute(delete(Lead)); db.execute(delete(Customer)); db.execute(delete(User)); roles={x.name:x.id for x in db.scalars(select(Role))}
   self.admin=self.user("admin",roles["Admin"]); self.manager=self.user("manager",roles["Manager"]); self.sales=self.user("sales",roles["Sales Executive"],self.manager.id); self.other=self.user("other",roles["Sales Executive"]); self.inactive=self.user("inactive",roles["Sales Executive"]); self.inactive.is_active=False; db.add_all([self.admin,self.manager,self.sales,self.other,self.inactive])
  self.client.cookies.clear()
 @staticmethod
 def user(prefix,role_id,manager_id=None):
  suffix=uuid4().hex[:8]; return User(id=uuid4(),name=prefix,email=f"{prefix}{suffix}@example.com",username=f"{prefix}{suffix}",password_hash=hash_password("Valid#Password1"),role_id=role_id,manager_id=manager_id,is_active=True)
 def login(self,user):
  self.client.cookies.clear(); self.client.get("/api/auth/csrf"); r=self.client.post("/api/auth/login",json={"identity":user.username,"password":"Valid#Password1"},headers={"X-CSRF-Token":self.client.cookies.get("acxiomcrm_csrf")}); self.assertEqual(r.status_code,200)
 def customer(self,user,**changes):
  self.login(user); digits=f"{uuid4().int % 10**7:07d}"; p={"name":"Opportunity Customer","email":f"customer{uuid4().hex[:8]}@example.com","phone":f"+1 415 {digits[:3]}-{digits[3:]}"}; p.update(changes); return self.client.post("/api/customers",json=p,headers={"X-CSRF-Token":self.client.cookies.get("acxiomcrm_csrf")}).json()
 def payload(self,customer_id,**changes):
  p={"name":"New Opportunity","customer_id":customer_id,"amount":"1000.00","probability":"25","expected_close_date":str(date.today()+timedelta(days=10)),"notes":"Safe note"}; p.update(changes); return p
 def create(self,user,customer_id,**changes):
  self.login(user); return self.client.post("/api/opportunities",json=self.payload(customer_id,**changes),headers={"X-CSRF-Token":self.client.cookies.get("acxiomcrm_csrf")})
 def test_create_scopes_and_unauthenticated(self):
  customer=self.customer(self.sales); opportunity=self.create(self.sales,customer["id"]).json(); self.login(self.sales); self.assertEqual(self.client.get(f"/api/opportunities/{opportunity['id']}").status_code,200)
  self.login(self.manager); self.assertEqual(self.client.get(f"/api/opportunities/{opportunity['id']}").status_code,200)
  other_customer=self.customer(self.other); other=self.create(self.other,other_customer["id"]).json(); self.login(self.sales); self.assertEqual(self.client.get(f"/api/opportunities/{other['id']}").status_code,403); self.client.cookies.clear(); self.assertEqual(self.client.get("/api/opportunities").status_code,401)
 def test_validation_and_active_date_rules(self):
  customer=self.customer(self.admin); self.login(self.admin); h={"X-CSRF-Token":self.client.cookies.get("acxiomcrm_csrf")}
  for change in ({"amount":"0"},{"amount":"-1"},{"probability":"-1"},{"probability":"101"}): self.assertEqual(self.client.post("/api/opportunities",json=self.payload(customer["id"],**change),headers=h).status_code,422)
  self.assertEqual(self.client.post("/api/opportunities",json=self.payload(str(uuid4())),headers=h).status_code,400)
  self.assertEqual(self.client.post("/api/opportunities",json=self.payload(customer["id"],owner_id=str(uuid4())),headers=h).status_code,400)
  self.assertEqual(self.client.post("/api/opportunities",json=self.payload(customer["id"],owner_id=str(self.inactive.id)),headers=h).status_code,400)
  self.assertEqual(self.client.post("/api/opportunities",json=self.payload(customer["id"],expected_close_date=str(date.today()-timedelta(days=1))),headers=h).status_code,400)
 def test_update_weighted_pipeline_and_transitions(self):
  customer=self.customer(self.admin); opportunity=self.create(self.admin,customer["id"],amount="900",probability="40").json(); self.assertEqual(str(opportunity["weighted_pipeline"]),"360.00")
  self.login(self.admin); h={"X-CSRF-Token":self.client.cookies.get("acxiomcrm_csrf")}; updated=self.client.put(f"/api/opportunities/{opportunity['id']}",json={"name":"Updated Opportunity","amount":"2000","probability":"50"},headers=h); self.assertEqual(updated.status_code,200); self.assertEqual(str(updated.json()["weighted_pipeline"]),"1000.00")
  self.assertEqual(self.client.post(f"/api/opportunities/{opportunity['id']}/stage",json={"stage":"proposal"},headers=h).status_code,200)
  self.assertEqual(self.client.post(f"/api/opportunities/{opportunity['id']}/stage",json={"stage":"won"},headers=h).status_code,400)
  self.assertEqual(self.client.post(f"/api/opportunities/{opportunity['id']}/stage",json={"stage":"negotiation"},headers=h).status_code,200)
  self.assertEqual(self.client.post(f"/api/opportunities/{opportunity['id']}/stage",json={"stage":"won"},headers=h).status_code,200)
  self.assertEqual(self.client.post(f"/api/opportunities/{opportunity['id']}/stage",json={"stage":"proposal"},headers=h).status_code,400)
  history=self.client.get(f"/api/opportunities/{opportunity['id']}/history").json(); self.assertIn("opportunity_stage_changed",{x["action"] for x in history})
 def test_search_filters_pagination_and_unauthorized_stage(self):
  customer=self.customer(self.admin); one=self.create(self.admin,customer["id"],name="Alpha Opportunity",amount="10").json(); two=self.create(self.admin,customer["id"],name="Beta Opportunity",owner_id=str(self.sales.id),amount="20").json(); three=self.create(self.admin,customer["id"],name="Gamma Opportunity",amount="30").json()
  self.login(self.admin); h={"X-CSRF-Token":self.client.cookies.get("acxiomcrm_csrf")}; self.client.post(f"/api/opportunities/{two['id']}/stage",json={"stage":"proposal"},headers=h)
  self.assertEqual(self.client.get("/api/opportunities",params={"search":"alpha"}).json()["items"][0]["id"],one["id"])
  self.assertEqual({x["id"] for x in self.client.get("/api/opportunities",params={"stage":"proposal"}).json()["items"]},{two["id"]})
  self.assertEqual({x["id"] for x in self.client.get("/api/opportunities",params={"owner_id":str(self.sales.id)}).json()["items"]},{two["id"]})
  first=self.client.get("/api/opportunities",params={"page":1,"page_size":2,"sort_by":"opportunity_code"}).json(); second=self.client.get("/api/opportunities",params={"page":2,"page_size":2,"sort_by":"opportunity_code"}).json(); self.assertEqual(first["total"],3); self.assertEqual(len(first["items"]),2); self.assertEqual(len(second["items"]),1); self.assertTrue({x["id"] for x in first["items"]}.isdisjoint({x["id"] for x in second["items"]}))
  self.login(self.other); self.assertEqual(self.client.post(f"/api/opportunities/{one['id']}/stage",json={"stage":"proposal"},headers={"X-CSRF-Token":self.client.cookies.get("acxiomcrm_csrf")}).status_code,403)
 def test_admin_create_sales_own_manager_team_and_unauthenticated_are_explicit(self):
  admin_customer=self.customer(self.admin); admin_created=self.create(self.admin,admin_customer["id"])
  self.assertEqual(admin_created.status_code,201)
  sales_customer=self.customer(self.sales); sales_created=self.create(self.sales,sales_customer["id"]).json()
  self.login(self.sales); self.assertEqual(self.client.get(f"/api/opportunities/{sales_created['id']}").status_code,200)
  self.login(self.manager); self.assertEqual(self.client.get(f"/api/opportunities/{sales_created['id']}").status_code,200)
  self.client.cookies.clear(); self.assertEqual(self.client.get("/api/opportunities").status_code,401)
 def test_invalid_stage_and_client_weighted_pipeline_are_not_accepted_as_authoritative(self):
  customer=self.customer(self.admin); self.login(self.admin); h={"X-CSRF-Token":self.client.cookies.get("acxiomcrm_csrf")}
  response=self.client.post("/api/opportunities",json=self.payload(customer["id"],amount="1200",probability="25",weighted_pipeline="999999"),headers=h)
  self.assertEqual(response.status_code,201); self.assertEqual(str(response.json()["weighted_pipeline"]),"300.00")
  invalid=self.client.post(f"/api/opportunities/{response.json()['id']}/stage",json={"stage":"invalid-stage"},headers=h)
  self.assertEqual(invalid.status_code,422)
 def test_lost_terminal_and_past_date_update_rejected(self):
  customer=self.customer(self.admin); opportunity=self.create(self.admin,customer["id"]).json(); self.login(self.admin); h={"X-CSRF-Token":self.client.cookies.get("acxiomcrm_csrf")}
  self.assertEqual(self.client.put(f"/api/opportunities/{opportunity['id']}",json={"expected_close_date":str(date.today()-timedelta(days=1))},headers=h).status_code,400)
  self.assertEqual(self.client.post(f"/api/opportunities/{opportunity['id']}/stage",json={"stage":"lost"},headers=h).status_code,200)
  self.assertEqual(self.client.post(f"/api/opportunities/{opportunity['id']}/stage",json={"stage":"proposal"},headers=h).status_code,400)
 def test_customer_and_lead_scope_validation(self):
  admin_customer=self.customer(self.admin)
  self.login(self.other); lead_payload={"name":"Other Lead","email":"other-lead@example.com","phone":"+1 415 555 0777","source":"Referral"}
  other_lead=self.client.post("/api/leads",json=lead_payload,headers={"X-CSRF-Token":self.client.cookies.get("acxiomcrm_csrf")}).json()
  sales_customer=self.customer(self.sales); self.login(self.sales); h={"X-CSRF-Token":self.client.cookies.get("acxiomcrm_csrf")}
  self.assertEqual(self.client.post("/api/opportunities",json=self.payload(admin_customer["id"]),headers=h).status_code,403)
  self.assertEqual(self.client.post("/api/opportunities",json=self.payload(sales_customer["id"],lead_id=other_lead["id"]),headers=h).status_code,403)
 def test_customer_filter_restricts_records(self):
  first_customer=self.customer(self.admin,name="First Customer"); second_customer=self.customer(self.admin,name="Second Customer")
  first=self.create(self.admin,first_customer["id"],name="First Customer Opportunity").json(); self.create(self.admin,second_customer["id"],name="Second Customer Opportunity")
  self.login(self.admin); result=self.client.get("/api/opportunities",params={"customer_id":first_customer["id"]}).json()
  self.assertEqual(result["total"],1); self.assertEqual(result["items"][0]["id"],first["id"])

import os,unittest
from pathlib import Path
from uuid import uuid4
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,delete,event,select
from sqlalchemy.orm import sessionmaker
from test_support import TEST_DATABASE as DB
from app.api.deps import get_db
from app.core.config import get_settings
from app.core.security import hash_password
from app.main import app
from app.models.audit_log import AuditLog
from app.models.user import User
from app.models.role import Role
class UserManagementTests(unittest.TestCase):
 @classmethod
 def setUpClass(c):
  get_settings.cache_clear();DB.unlink(missing_ok=True);command.upgrade(Config(str(Path(__file__).resolve().parents[1]/"alembic.ini")),"head");c.engine=create_engine(os.environ["DATABASE_URL"],connect_args={"check_same_thread":False});event.listen(c.engine,"connect",lambda x,_:x.execute("PRAGMA foreign_keys=ON"));c.S=sessionmaker(bind=c.engine,expire_on_commit=False)
  def over():
   d=c.S()
   try:yield d
   finally:d.close()
  app.dependency_overrides[get_db]=over;c.client=TestClient(app)
 @classmethod
 def tearDownClass(c):app.dependency_overrides.clear();c.engine.dispose();DB.unlink(missing_ok=True)
 def setUp(s):
  with s.S.begin() as d:
   d.execute(delete(AuditLog));d.execute(delete(User));roles={x.name:x.id for x in d.scalars(select(Role))};s.admin=s.u("admin",roles["Admin"]);s.manager=s.u("manager",roles["Manager"]);s.sales=s.u("sales",roles["Sales Executive"],s.manager.id);s.other=s.u("other",roles["Sales Executive"]);s.inactive=s.u("inactive",roles["Manager"]);s.inactive.is_active=False;d.add_all([s.admin,s.manager,s.sales,s.other,s.inactive])
  s.client.cookies.clear()
 @staticmethod
 def u(n,r,m=None):
  x=uuid4().hex[:8];return User(id=uuid4(),name=n,email=f"{n}{x}@example.com",username=f"{n}{x}",password_hash=hash_password("Valid#Password1"),role_id=r,manager_id=m,is_active=True)
 def login(s,u,password="Valid#Password1"):
  s.client.cookies.clear();s.client.get("/api/auth/csrf");r=s.client.post("/api/auth/login",json={"identity":u.username,"password":password},headers={"X-CSRF-Token":s.client.cookies.get("acxiomcrm_csrf")});s.assertEqual(r.status_code,200)
 def payload(s,**x):
  n=uuid4().hex[:8];p={"name":"New User","username":f"user{n}","email":f"user{n}@example.com","password":"Valid#Password1","role":"Sales Executive"};p.update(x);return p
 def post(s,p):return s.client.post("/api/users",json=p,headers={"X-CSRF-Token":s.client.cookies.get("acxiomcrm_csrf")})
 def test_admin_only_user_management_and_safe_dtos(s):
  s.login(s.admin);response=s.client.get("/api/users");s.assertEqual(response.status_code,200);text=str(response.json());
  for secret in ("password_hash","token_version","failed_login_count","lockout_until"):s.assertNotIn(secret,text)
  for user in (s.manager,s.sales):
   s.login(user);s.assertEqual(s.client.get("/api/users").status_code,403);s.assertEqual(s.post(s.payload()).status_code,403);s.assertEqual(s.client.put(f"/api/users/{s.sales.id}",json={"name":"x"},headers={"X-CSRF-Token":s.client.cookies.get("acxiomcrm_csrf")}).status_code,403);s.assertEqual(s.client.post(f"/api/users/{s.sales.id}/reset-password",json={"password":"Valid#Password2"},headers={"X-CSRF-Token":s.client.cookies.get("acxiomcrm_csrf")}).status_code,403)
  s.client.cookies.clear();s.assertEqual(s.client.get("/api/users").status_code,401)
 def test_create_duplicates_password_roles_and_manager_rules(s):
  s.login(s.admin);created=s.post(s.payload(manager_id=str(s.manager.id)));s.assertEqual(created.status_code,201);uid=created.json()["id"]
  s.assertEqual(s.post(s.payload(username=created.json()["username"])).status_code,409);s.assertEqual(s.post(s.payload(email=created.json()["email"])).status_code,409);s.assertEqual(s.post(s.payload(password="weak")).status_code,422);s.assertEqual(s.post(s.payload(role="Bad")).status_code,422);s.assertEqual(s.post(s.payload(manager_id=str(uuid4()))).status_code,404);s.assertEqual(s.post(s.payload(manager_id=str(s.inactive.id))).status_code,400);s.assertEqual(s.post(s.payload(manager_id=str(s.sales.id))).status_code,400);s.assertEqual(s.post(s.payload(role="Manager",manager_id=str(s.manager.id))).status_code,400);s.assertEqual(s.post(s.payload(role="Admin",manager_id=str(s.manager.id))).status_code,400)
  history=s.client.get(f"/api/users/{uid}").json();s.assertNotIn("password",str(history))
 def test_update_role_manager_activation_and_password_reset(s):
  s.login(s.admin);created=s.post(s.payload()).json();uid=created["id"];h={"X-CSRF-Token":s.client.cookies.get("acxiomcrm_csrf")}
  s.assertEqual(s.client.put(f"/api/users/{uid}",json={"name":"Updated","manager_id":str(s.manager.id)},headers=h).status_code,200);s.assertEqual(s.client.put(f"/api/users/{uid}",json={"role":"Manager","manager_id":str(s.manager.id)},headers=h).status_code,400);s.assertEqual(s.client.put(f"/api/users/{uid}",json={"role":"Manager"},headers=h).status_code,200)
  s.assertEqual(s.client.post(f"/api/users/{uid}/deactivate",headers=h).status_code,200);s.assertEqual(s.client.post(f"/api/users/{s.admin.id}/deactivate",headers=h).status_code,400);s.client.cookies.clear();s.client.get("/api/auth/csrf");s.assertEqual(s.client.post("/api/auth/login",json={"identity":created["username"],"password":"Valid#Password1"},headers={"X-CSRF-Token":s.client.cookies.get("acxiomcrm_csrf")}).status_code,401)
  s.login(s.admin);h={"X-CSRF-Token":s.client.cookies.get("acxiomcrm_csrf")};s.assertEqual(s.client.post(f"/api/users/{uid}/activate",headers=h).status_code,200);s.assertEqual(s.client.post(f"/api/users/{uid}/reset-password",json={"password":"Valid#Password2"},headers=h).status_code,204);s.client.cookies.clear();s.client.get("/api/auth/csrf");s.assertEqual(s.client.post("/api/auth/login",json={"identity":created["username"],"password":"Valid#Password2"},headers={"X-CSRF-Token":s.client.cookies.get("acxiomcrm_csrf")}).status_code,200)
  with s.S()as d:actions={x.action for x in d.scalars(select(AuditLog).where(AuditLog.entity_name=="user",AuditLog.record_id==uid))};s.assertTrue({"user_created","manager_changed","role_changed","user_deactivated","user_activated","password_reset"}.issubset(actions))
 def test_search_filters_sort_pagination_and_scope(s):
  s.login(s.admin)
  for name in ("Alpha","Beta","Gamma"):s.assertEqual(s.post(s.payload(name=name,username=name.lower())).status_code,201)
  search=s.client.get("/api/users",params={"search":"alpha"}).json();role=s.client.get("/api/users",params={"role":"Sales Executive"}).json();active=s.client.get("/api/users",params={"is_active":True}).json();first=s.client.get("/api/users",params={"page":1,"page_size":2,"sort_by":"username"}).json();second=s.client.get("/api/users",params={"page":2,"page_size":2,"sort_by":"username"}).json();s.assertEqual(search["total"],1);s.assertGreaterEqual(role["total"],4);s.assertGreaterEqual(active["total"],1);s.assertEqual(first["page_size"],2);s.assertTrue({x["id"]for x in first["items"]}.isdisjoint({x["id"]for x in second["items"]}))

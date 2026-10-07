import os,tempfile,unittest
from datetime import date,timedelta,datetime,timezone
from pathlib import Path
from uuid import UUID,uuid4
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,delete,event,select
from sqlalchemy.orm import sessionmaker
DB=Path(tempfile.gettempdir())/"acxiomcrm-engagement-tests.db";os.environ["DATABASE_URL"]=f"sqlite+pysqlite:///{DB.as_posix()}";os.environ["AUTH_SECRET_KEY"]="unit-test-secret-not-for-production-123456";os.environ["COOKIE_SECURE"]="false"
from app.api.deps import get_db
from app.core.config import get_settings
from app.core.security import hash_password
from app.main import app
from app.models.audit_log import AuditLog
from app.models.follow_up import FollowUp
from app.models.activity import Activity
from app.models.customer import Customer
from app.models.user import User
from app.models.role import Role
from app.models.lead import Lead
from app.models.opportunity import Opportunity
class EngagementTests(unittest.TestCase):
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
   d.execute(delete(AuditLog));d.execute(delete(FollowUp));d.execute(delete(Activity));d.execute(delete(Customer));d.execute(delete(User));r={x.name:x.id for x in d.scalars(select(Role))};s.admin=s.u("admin",r["Admin"]);s.manager=s.u("manager",r["Manager"]);s.sales=s.u("sales",r["Sales Executive"],s.manager.id);s.other=s.u("other",r["Sales Executive"]);s.inactive=s.u("inactive",r["Sales Executive"]);s.inactive.is_active=False;d.add_all([s.admin,s.manager,s.sales,s.other,s.inactive])
  s.client.cookies.clear()
 @staticmethod
 def u(n,r,m=None):
  x=uuid4().hex[:7];return User(id=uuid4(),name=n,email=f"{n}{x}@x.com",username=f"{n}{x}",password_hash=hash_password("Valid#Password1"),role_id=r,manager_id=m,is_active=True)
 def login(s,u):s.client.cookies.clear();s.client.get("/api/auth/csrf");s.assertEqual(s.client.post("/api/auth/login",json={"identity":u.username,"password":"Valid#Password1"},headers={"X-CSRF-Token":s.client.cookies.get("acxiomcrm_csrf")}).status_code,200)
 def customer(s,u):
  s.login(u);x=uuid4().hex[:7];digits=f"{uuid4().int % 10**7:07d}";return s.client.post("/api/customers",json={"name":"Target","email":f"{x}@x.com","phone":f"+1 415 {digits[:3]}-{digits[3:]}"},headers={"X-CSRF-Token":s.client.cookies.get("acxiomcrm_csrf")}).json()
 def fp(s,c,**x):
  p={"customer_id":c,"follow_up_date":str(date.today()+timedelta(days=1)),"follow_up_type":"call","subject":"Call"};p.update(x);return p
 def ap(s,c,**x):
  p={"customer_id":c,"activity_type":"call","subject":"Activity","activity_date":datetime.now(timezone.utc).isoformat()};p.update(x);return p
 def test_follow_up_validation_scope_and_workflows(s):
  c=s.customer(s.sales);s.login(s.sales);h={"X-CSRF-Token":s.client.cookies.get("acxiomcrm_csrf")};good=s.client.post("/api/follow-ups",json=s.fp(c["id"]),headers=h);s.assertEqual(good.status_code,201);fid=good.json()["id"]
  s.assertEqual(s.client.post("/api/follow-ups",json=s.fp(c["id"],lead_id=str(uuid4())),headers=h).status_code,422);s.assertEqual(s.client.post("/api/follow-ups",json=s.fp(c["id"],follow_up_date=str(date.today()-timedelta(days=1))),headers=h).status_code,400);s.assertEqual(s.client.post("/api/follow-ups",json=s.fp(c["id"],assigned_user_id=str(s.other.id)),headers=h).status_code,403)
  s.assertEqual(s.client.post(f"/api/follow-ups/{fid}/reschedule",json={"follow_up_date":str(date.today()+timedelta(days=2))},headers=h).status_code,200);s.assertEqual(s.client.post(f"/api/follow-ups/{fid}/complete",headers=h).status_code,200);s.assertEqual(s.client.post(f"/api/follow-ups/{fid}/cancel",headers=h).status_code,400);hist=s.client.get(f"/api/follow-ups/{fid}/history").json();s.assertTrue({"follow_up_created","follow_up_rescheduled","follow_up_completed"}.issubset({x["action"]for x in hist}))
  other=s.customer(s.other);s.login(s.other);oid=s.client.post("/api/follow-ups",json=s.fp(other["id"]),headers={"X-CSRF-Token":s.client.cookies.get("acxiomcrm_csrf")}).json()["id"];s.login(s.sales);s.assertEqual(s.client.get(f"/api/follow-ups/{oid}").status_code,403);s.client.cookies.clear();s.assertEqual(s.client.get("/api/follow-ups").status_code,401)
 def test_follow_up_filters_pagination_and_manager_scope(s):
  c=s.customer(s.sales);s.login(s.sales);h={"X-CSRF-Token":s.client.cookies.get("acxiomcrm_csrf")}
  ids=[s.client.post("/api/follow-ups",json=s.fp(c["id"],subject=f"F{i}"),headers=h).json()["id"]for i in range(3)];s.login(s.manager);s.assertEqual(s.client.get(f"/api/follow-ups/{ids[0]}").status_code,200);a=s.client.get("/api/follow-ups",params={"status":"planned","page_size":2,"page":1}).json();b=s.client.get("/api/follow-ups",params={"status":"planned","page_size":2,"page":2}).json();s.assertEqual(a["total"],3);s.assertTrue({x["id"]for x in a["items"]}.isdisjoint({x["id"]for x in b["items"]}));s.assertEqual(s.client.get("/api/follow-ups",params={"upcoming":True}).json()["total"],3)
 def test_activity_validation_scope_update_filters_pagination_audit(s):
  c=s.customer(s.sales);s.login(s.sales);h={"X-CSRF-Token":s.client.cookies.get("acxiomcrm_csrf")};first=s.client.post("/api/activities",json=s.ap(c["id"]),headers=h);s.assertEqual(first.status_code,201);aid=first.json()["id"]
  s.assertEqual(s.client.post("/api/activities",json=s.ap(c["id"],activity_type="bad"),headers=h).status_code,422);s.assertEqual(s.client.post("/api/activities",json=s.ap(c["id"],assigned_user_id=str(s.other.id)),headers=h).status_code,403);s.assertEqual(s.client.put(f"/api/activities/{aid}",json={"subject":"Updated"},headers=h).status_code,200)
  for i in range(2):s.client.post("/api/activities",json=s.ap(c["id"],subject=f"A{i}"),headers=h)
  one=s.client.get("/api/activities",params={"activity_type":"call","page_size":2}).json();two=s.client.get("/api/activities",params={"activity_type":"call","page":2,"page_size":2}).json();s.assertEqual(one["total"],3);s.assertTrue({x["id"]for x in one["items"]}.isdisjoint({x["id"]for x in two["items"]}));s.assertIn("activity_updated",{x["action"]for x in s.client.get(f"/api/activities/{aid}/history").json()})
 def test_follow_up_target_input_and_enum_validation(s):
  c=s.customer(s.admin);s.login(s.admin);h={"X-CSRF-Token":s.client.cookies.get("acxiomcrm_csrf")}
  base={"follow_up_date":str(date.today()+timedelta(days=1)),"follow_up_type":"call","subject":"Target test"}
  s.assertEqual(s.client.post("/api/follow-ups",json=base,headers=h).status_code,422)
  s.assertEqual(s.client.post("/api/follow-ups",json={**base,"customer_id":c["id"],"lead_id":str(uuid4())},headers=h).status_code,422)
  for key in ("customer_id","lead_id","opportunity_id"):
   s.assertEqual(s.client.post("/api/follow-ups",json={**base,key:str(uuid4())},headers=h).status_code,400)
  s.assertEqual(s.client.post("/api/follow-ups",json={**base,"customer_id":c["id"],"status":"bad"},headers=h).status_code,422)
  s.assertEqual(s.client.post("/api/follow-ups",json={**base,"customer_id":c["id"],"follow_up_type":"bad"},headers=h).status_code,422)
  s.assertEqual(s.client.post("/api/follow-ups",json={**base,"customer_id":c["id"],"assigned_user_id":str(uuid4())},headers=h).status_code,400)
  s.assertEqual(s.client.post("/api/follow-ups",json={**base,"customer_id":c["id"],"assigned_user_id":str(s.inactive.id)},headers=h).status_code,400)
 def test_follow_up_update_cancel_filters_and_all_audits(s):
  c=s.customer(s.admin);s.login(s.admin);h={"X-CSRF-Token":s.client.cookies.get("acxiomcrm_csrf")};created=s.client.post("/api/follow-ups",json=s.fp(c["id"],subject="Original"),headers=h).json();fid=created["id"]
  updated=s.client.put(f"/api/follow-ups/{fid}",json={"subject":"Updated"},headers=h);s.assertEqual(updated.status_code,200);s.assertEqual(updated.json()["subject"],"Updated")
  s.assertEqual(s.client.post(f"/api/follow-ups/{fid}/cancel",headers=h).status_code,200);s.assertEqual(s.client.post(f"/api/follow-ups/{fid}/complete",headers=h).status_code,400)
  history={x["action"]for x in s.client.get(f"/api/follow-ups/{fid}/history").json()};s.assertTrue({"follow_up_created","follow_up_updated","follow_up_cancelled"}.issubset(history))
  for i in range(3):s.client.post("/api/follow-ups",json=s.fp(c["id"],subject=f"Planned {i}"),headers=h)
  status=s.client.get("/api/follow-ups",params={"status":"planned"}).json();assigned=s.client.get("/api/follow-ups",params={"assigned_user_id":str(s.admin.id)}).json();target=s.client.get("/api/follow-ups",params={"target_type":"customer"}).json();page1=s.client.get("/api/follow-ups",params={"page":1,"page_size":2}).json();page2=s.client.get("/api/follow-ups",params={"page":2,"page_size":2}).json();s.assertEqual(status["total"],3);s.assertEqual(assigned["total"],4);s.assertEqual(target["total"],4);s.assertTrue({x["id"]for x in page1["items"]}.isdisjoint({x["id"]for x in page2["items"]}))
 def test_follow_up_overdue_filter_from_existing_historical_record(s):
  c=s.customer(s.admin)
  with s.S.begin() as d:d.add(FollowUp(customer_id=UUID(c["id"]),follow_up_date=date.today()-timedelta(days=1),follow_up_type="call",subject="Historical",status="planned",assigned_user_id=s.admin.id))
  s.login(s.admin);overdue=s.client.get("/api/follow-ups",params={"overdue":True}).json();s.assertEqual(overdue["total"],1);s.assertEqual(overdue["items"][0]["subject"],"Historical")
 def test_activity_all_types_assignee_validation_and_audits(s):
  c=s.customer(s.admin);s.login(s.admin);h={"X-CSRF-Token":s.client.cookies.get("acxiomcrm_csrf")};ids=[]
  for typ in ("call","meeting","email","task"):
   response=s.client.post("/api/activities",json=s.ap(c["id"],activity_type=typ,subject=typ),headers=h);s.assertEqual(response.status_code,201);ids.append(response.json()["id"])
  s.assertEqual(s.client.post("/api/activities",json=s.ap(c["id"],assigned_user_id=str(uuid4())),headers=h).status_code,400);s.assertEqual(s.client.post("/api/activities",json=s.ap(c["id"],assigned_user_id=str(s.inactive.id)),headers=h).status_code,400)
  updated=s.client.put(f"/api/activities/{ids[0]}",json={"assigned_user_id":str(s.admin.id),"subject":"Reassigned"},headers=h);s.assertEqual(updated.status_code,200);history={x["action"]for x in s.client.get(f"/api/activities/{ids[0]}/history").json()};s.assertTrue({"activity_created","activity_assigned"}.issubset(history))
  for typ in ("call","meeting","email","task"):s.assertEqual(s.client.get("/api/activities",params={"activity_type":typ}).json()["total"],1)
  s.assertEqual(s.client.get("/api/activities",params={"assigned_user_id":str(s.admin.id)}).json()["total"],4)

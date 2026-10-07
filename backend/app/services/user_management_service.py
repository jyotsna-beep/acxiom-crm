from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import func,or_,select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session,joinedload
from app.core.security import PasswordPolicyError,hash_password
from app.models.role import Role
from app.models.user import User
from app.policies.authorization import RoleName
from app.schemas.user_management import *
from app.services.audit_service import write_audit

def _manager(x):return UserManager(id=x.id,username=x.username,email=x.email) if x else None
def _item(x):return UserItem(id=x.id,name=x.name,username=x.username,email=x.email,role=x.role.name,is_active=x.is_active,manager=_manager(x.manager),created_at=x.created_at.isoformat(),updated_at=x.updated_at.isoformat())
def _get(db,id):
 x=db.scalar(select(User).options(joinedload(User.role),joinedload(User.manager)).where(User.id==id))
 if not x:raise HTTPException(404,"User not found.")
 return x
def _role(db,name):
 x=db.scalar(select(Role).where(Role.name==name))
 if not x:raise HTTPException(400,"Invalid role.")
 return x
def _manager_or_error(db,role,manager_id,user_id=None):
 if role in {RoleName.ADMIN.value,RoleName.MANAGER.value}:
  if manager_id is not None:raise HTTPException(400,"Admins and Managers cannot have a manager.")
  return None
 if manager_id is None:return None
 if manager_id==user_id:raise HTTPException(400,"A user cannot manage themselves.")
 m=_get(db,manager_id)
 if not m.is_active or m.role.name!=RoleName.MANAGER.value:raise HTTPException(400,"Manager must be an active Manager user.")
 return m
def _snapshot(x):return {"role":x.role.name,"manager_id":str(x.manager_id)if x.manager_id else None,"is_active":x.is_active}
def list_users(db,*,search,role,is_active,manager_id,page,page_size,sort_by,sort_order):
 stmt=select(User).options(joinedload(User.role),joinedload(User.manager))
 if search:
  t=f"%{search.strip().lower()}%";stmt=stmt.where(or_(func.lower(User.name).like(t),func.lower(User.email).like(t),func.lower(User.username).like(t)))
 if role:stmt=stmt.join(Role).where(Role.name==role)
 if is_active is not None:stmt=stmt.where(User.is_active==is_active)
 if manager_id:stmt=stmt.where(User.manager_id==manager_id)
 columns={"name":User.name,"email":User.email,"username":User.username,"created_at":User.created_at};col=columns[sort_by];stmt=stmt.order_by(col.desc()if sort_order=="desc"else col.asc());total=db.scalar(select(func.count()).select_from(stmt.subquery()))or 0;rows=db.scalars(stmt.offset((page-1)*page_size).limit(page_size)).unique().all();return UserPage.create(items=[_item(x)for x in rows],page=page,page_size=page_size,total=total)
def create_user(db,*,admin,payload,ip_address):
 if db.scalar(select(User.id).where(or_(func.lower(User.email)==str(payload.email).lower(),User.username==payload.username))):raise HTTPException(409,"A user with that email or username already exists.")
 r=_role(db,payload.role);m=_manager_or_error(db,payload.role,payload.manager_id)
 try: hashed=hash_password(payload.password)
 except PasswordPolicyError as e:raise HTTPException(422,str(e))from e
 x=User(name=payload.name,email=str(payload.email).lower(),username=payload.username,password_hash=hashed,role_id=r.id,manager_id=m.id if m else None,is_active=payload.is_active);db.add(x);db.flush();db.refresh(x,attribute_names=["role","manager"]);write_audit(db,actor_id=admin.id,action="user_created",entity_name="user",record_id=x.id,new_value=_snapshot(x),ip_address=ip_address);db.commit();db.refresh(x,attribute_names=["role","manager"]);return _item(x)
def update_user(db,*,admin,id,payload,ip_address):
 x=_get(db,id);changes=payload.model_dump(exclude_unset=True);old=_snapshot(x);new_role=changes.get("role",x.role.name)
 if new_role in {RoleName.ADMIN.value,RoleName.MANAGER.value} and changes.get("manager_id") is not None and "manager_id" in changes:raise HTTPException(400,"Admins and Managers cannot have a manager.")
 requested_manager=None if new_role in {RoleName.ADMIN.value,RoleName.MANAGER.value} else changes.get("manager_id",x.manager_id);m=_manager_or_error(db,new_role,requested_manager,x.id)
 if "email"in changes or "username"in changes:
  email=str(changes.get("email",x.email)).lower();username=changes.get("username",x.username);duplicate=db.scalar(select(User.id).where(User.id!=x.id,or_(func.lower(User.email)==email,User.username==username)))
  if duplicate:raise HTTPException(409,"A user with that email or username already exists.")
 if "role"in changes:changes["role_id"]=_role(db,changes.pop("role")).id
 if "manager_id"in changes or new_role in {RoleName.ADMIN.value,RoleName.MANAGER.value}:changes["manager_id"]=m.id if m else None
 for k,v in changes.items():setattr(x,k,v)
 db.flush();db.refresh(x,attribute_names=["role","manager"]);action="role_changed"if old["role"]!=x.role.name else "manager_changed"if old["manager_id"]!=(str(x.manager_id)if x.manager_id else None)else "user_updated";write_audit(db,actor_id=admin.id,action=action,entity_name="user",record_id=x.id,old_value=old,new_value=_snapshot(x),ip_address=ip_address);db.commit();db.refresh(x,attribute_names=["role","manager"]);return _item(x)
def set_active(db,*,admin,id,active,ip_address):
 x=_get(db,id)
 if not active and x.id==admin.id:raise HTTPException(400,"You cannot deactivate your own account.")
 if x.is_active==active:return _item(x)
 old=_snapshot(x);x.is_active=active;x.token_version+=1;db.flush();write_audit(db,actor_id=admin.id,action="user_activated"if active else "user_deactivated",entity_name="user",record_id=x.id,old_value=old,new_value=_snapshot(x),ip_address=ip_address);db.commit();db.refresh(x,attribute_names=["role","manager"]);return _item(x)
def reset_password(db,*,admin,id,payload,ip_address):
 x=_get(db,id)
 try:x.password_hash=hash_password(payload.password)
 except PasswordPolicyError as e:raise HTTPException(422,str(e))from e
 x.token_version+=1;db.flush();write_audit(db,actor_id=admin.id,action="password_reset",entity_name="user",record_id=x.id,details="Administrator reset password.",ip_address=ip_address);db.commit()

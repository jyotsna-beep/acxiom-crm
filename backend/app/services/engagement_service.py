from datetime import date, datetime, timezone
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import func,or_,select
from sqlalchemy.orm import Session,joinedload
from app.models.follow_up import FollowUp
from app.models.activity import Activity
from app.models.customer import Customer
from app.models.lead import Lead
from app.models.opportunity import Opportunity
from app.models.user import User
from app.models.audit_log import AuditLog
from app.policies.authorization import authorized_user_ids,can_access_owner
from app.schemas.engagement import *
from app.services.audit_service import write_audit

def _user(u): return Assigned(id=u.id,username=u.username,email=u.email)
def _target(db,user,c,l,o):
 ids=[x for x in (c,l,o) if x is not None]
 if len(ids)!=1: raise HTTPException(400,"Exactly one related record is required.")
 model,ident=((Customer,c) if c else (Lead,l) if l else (Opportunity,o)); record=db.get(model,ident)
 if not record: raise HTTPException(400,"Related record not found.")
 if not can_access_owner(db,user,record.owner_id): raise HTTPException(403,"You do not have access to the related record.")
def _assignee(db,user,ident):
 ident=ident or user.id
 if not can_access_owner(db,user,ident): raise HTTPException(403,"You cannot assign to that user.")
 record=db.get(User,ident)
 if not record or not record.is_active: raise HTTPException(400,"Assigned user must be active.")
 return record
def _scope(db,user,stmt,model):
 ids=authorized_user_ids(db,user); return stmt if ids is None else stmt.where(model.assigned_user_id.in_(ids))
def _fu_item(x): return FollowUpItem(id=x.id,subject=x.subject,follow_up_date=x.follow_up_date,follow_up_type=x.follow_up_type,status=x.status,assigned_user=_user(x.assigned_user),customer_id=x.customer_id,lead_id=x.lead_id,opportunity_id=x.opportunity_id,completed_at=x.completed_at,notes=x.notes)
def _act_item(x): return ActivityItem(id=x.id,activity_type=x.activity_type,subject=x.subject,description=x.description,activity_date=x.activity_date,status=x.status,assigned_user=_user(x.assigned_user),customer_id=x.customer_id,lead_id=x.lead_id,opportunity_id=x.opportunity_id)
def _snap(x): return {"subject":x.subject,"status":x.status,"assigned_user_id":str(x.assigned_user_id),"customer_id":str(x.customer_id) if x.customer_id else None,"lead_id":str(x.lead_id) if x.lead_id else None,"opportunity_id":str(x.opportunity_id) if x.opportunity_id else None}
def _fu(db,id):
 x=db.scalar(select(FollowUp).options(joinedload(FollowUp.assigned_user)).where(FollowUp.id==id))
 if not x: raise HTTPException(404,"Follow-up not found.")
 return x
def _access_fu(db,u,x):
 _target(db,u,x.customer_id,x.lead_id,x.opportunity_id)
 if not can_access_owner(db,u,x.assigned_user_id): raise HTTPException(403,"You do not have access to this follow-up.")
def create_follow_up(db,*,current_user,payload,ip_address):
 _target(db,current_user,payload.customer_id,payload.lead_id,payload.opportunity_id)
 if payload.follow_up_date<date.today(): raise HTTPException(400,"Follow-up date cannot be earlier than today.")
 a=_assignee(db,current_user,payload.assigned_user_id); x=FollowUp(customer_id=payload.customer_id,lead_id=payload.lead_id,opportunity_id=payload.opportunity_id,follow_up_date=payload.follow_up_date,follow_up_type=payload.follow_up_type,subject=payload.subject.strip(),notes=payload.notes,status="planned",assigned_user_id=a.id);db.add(x);db.flush();db.refresh(x,attribute_names=["assigned_user"]);write_audit(db,actor_id=current_user.id,action="follow_up_created",entity_name="follow_up",record_id=x.id,new_value=_snap(x),ip_address=ip_address);db.commit();db.refresh(x,attribute_names=["assigned_user"]);return _fu_item(x)
def list_follow_ups(db,*,current_user,status,assigned_user_id,target_type,upcoming,overdue,page,page_size):
 stmt=_scope(db,current_user,select(FollowUp).options(joinedload(FollowUp.assigned_user)),FollowUp)
 if status:stmt=stmt.where(FollowUp.status==status)
 if assigned_user_id: stmt=stmt.where(FollowUp.assigned_user_id==assigned_user_id)
 if target_type: stmt=stmt.where(getattr(FollowUp,f"{target_type}_id").is_not(None))
 if upcoming:stmt=stmt.where(FollowUp.status=="planned",FollowUp.follow_up_date>=date.today())
 if overdue:stmt=stmt.where(FollowUp.status=="planned",FollowUp.follow_up_date<date.today())
 total=db.scalar(select(func.count()).select_from(stmt.subquery()))or 0;rows=db.scalars(stmt.order_by(FollowUp.follow_up_date).offset((page-1)*page_size).limit(page_size)).all();return FollowUpPage.create(items=[_fu_item(x) for x in rows],page=page,page_size=page_size,total=total)
def update_follow_up(db,*,current_user,id,payload,ip_address):
 x=_fu(db,id);_access_fu(db,current_user,x)
 if x.status!="planned":raise HTTPException(400,"Terminal follow-ups cannot be edited.")
 changes=payload.model_dump(exclude_unset=True); c=changes.get("customer_id",x.customer_id);l=changes.get("lead_id",x.lead_id);o=changes.get("opportunity_id",x.opportunity_id);_target(db,current_user,c,l,o)
 if changes.get("follow_up_date",x.follow_up_date)<date.today():raise HTTPException(400,"Follow-up date cannot be earlier than today.")
 if "assigned_user_id" in changes:changes["assigned_user_id"]=_assignee(db,current_user,changes["assigned_user_id"]).id
 old=_snap(x)
 for k,v in changes.items():setattr(x,k,v)
 db.flush();write_audit(db,actor_id=current_user.id,action="follow_up_assigned" if "assigned_user_id" in changes else "follow_up_updated",entity_name="follow_up",record_id=x.id,old_value=old,new_value=_snap(x),ip_address=ip_address);db.commit();db.refresh(x,attribute_names=["assigned_user"]);return _fu_item(x)
def transition_follow_up(db,*,current_user,id,action,payload=None,ip_address=None):
 x=_fu(db,id);_access_fu(db,current_user,x)
 if x.status!="planned":raise HTTPException(400,"Follow-up is already terminal.")
 old=_snap(x)
 if action=="rescheduled":
  if payload.follow_up_date<date.today():raise HTTPException(400,"Follow-up date cannot be earlier than today.")
  x.follow_up_date=payload.follow_up_date
 elif action=="completed":x.status="completed";x.completed_at=datetime.now(timezone.utc)
 elif action=="cancelled":x.status="cancelled"
 else:raise HTTPException(400,"Invalid follow-up action.")
 db.flush();write_audit(db,actor_id=current_user.id,action=f"follow_up_{action}",entity_name="follow_up",record_id=x.id,old_value=old,new_value=_snap(x),ip_address=ip_address);db.commit();db.refresh(x,attribute_names=["assigned_user"]);return _fu_item(x)
def follow_history(db,*,current_user,id):
 x=_fu(db,id);_access_fu(db,current_user,x);return _history(db,"follow_up",id)
def _activity(db,id):
 x=db.scalar(select(Activity).options(joinedload(Activity.assigned_user)).where(Activity.id==id))
 if not x:raise HTTPException(404,"Activity not found.")
 return x
def create_activity(db,*,current_user,payload,ip_address):
 _target(db,current_user,payload.customer_id,payload.lead_id,payload.opportunity_id);a=_assignee(db,current_user,payload.assigned_user_id);x=Activity(**payload.model_dump(exclude={"assigned_user_id"}),assigned_user_id=a.id,status="open");db.add(x);db.flush();db.refresh(x,attribute_names=["assigned_user"]);write_audit(db,actor_id=current_user.id,action="activity_created",entity_name="activity",record_id=x.id,new_value=_snap(x),ip_address=ip_address);db.commit();db.refresh(x,attribute_names=["assigned_user"]);return _act_item(x)
def list_activities(db,*,current_user,activity_type,assigned_user_id,page,page_size):
 stmt=_scope(db,current_user,select(Activity).options(joinedload(Activity.assigned_user)),Activity)
 if activity_type:stmt=stmt.where(Activity.activity_type==activity_type)
 if assigned_user_id:stmt=stmt.where(Activity.assigned_user_id==assigned_user_id)
 total=db.scalar(select(func.count()).select_from(stmt.subquery()))or 0;rows=db.scalars(stmt.order_by(Activity.activity_date.desc()).offset((page-1)*page_size).limit(page_size)).all();return ActivityPage.create(items=[_act_item(x) for x in rows],page=page,page_size=page_size,total=total)
def update_activity(db,*,current_user,id,payload,ip_address):
 x=_activity(db,id);_target(db,current_user,x.customer_id,x.lead_id,x.opportunity_id);changes=payload.model_dump(exclude_unset=True);_target(db,current_user,changes.get("customer_id",x.customer_id),changes.get("lead_id",x.lead_id),changes.get("opportunity_id",x.opportunity_id))
 if "assigned_user_id" in changes:changes["assigned_user_id"]=_assignee(db,current_user,changes["assigned_user_id"]).id
 old=_snap(x)
 for k,v in changes.items():setattr(x,k,v)
 db.flush();write_audit(db,actor_id=current_user.id,action="activity_assigned" if "assigned_user_id" in changes else "activity_updated",entity_name="activity",record_id=x.id,old_value=old,new_value=_snap(x),ip_address=ip_address);db.commit();db.refresh(x,attribute_names=["assigned_user"]);return _act_item(x)
def get_activity(db,*,current_user,id):
 x=_activity(db,id);_target(db,current_user,x.customer_id,x.lead_id,x.opportunity_id);return _act_item(x)
def _history(db,entity,id):
 rows=db.scalars(select(AuditLog).where(AuditLog.entity_name==entity,AuditLog.record_id==str(id)).order_by(AuditLog.created_at.desc()));return [History(id=x.id,action=x.action,result=x.result,created_at=x.created_at.isoformat(),actor_id=x.user_id,details=x.details)for x in rows]

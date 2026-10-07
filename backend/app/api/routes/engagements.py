from typing import Literal
from uuid import UUID
from fastapi import APIRouter,Depends,Query,Request,status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user,require_csrf
from app.core.database import get_db
from app.models.user import User
from app.schemas.engagement import *
from app.services import engagement_service as s
follow_router=APIRouter(prefix="/api/follow-ups",tags=["follow-ups"]);activity_router=APIRouter(prefix="/api/activities",tags=["activities"])
def ip(r):return r.client.host if r.client else None
@follow_router.get("",response_model=FollowUpPage)
def fl(status:FollowUpStatus|None=None,assigned_user_id:UUID|None=None,target_type:Literal["customer","lead","opportunity"]|None=None,upcoming:bool=False,overdue:bool=False,page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):return s.list_follow_ups(db,current_user=current_user,status=status,assigned_user_id=assigned_user_id,target_type=target_type,upcoming=upcoming,overdue=overdue,page=page,page_size=page_size)
@follow_router.post("",response_model=FollowUpItem,status_code=status.HTTP_201_CREATED)
def fc(payload:FollowUpCreate,r:Request,db:Session=Depends(get_db),current_user:User=Depends(require_csrf)):return s.create_follow_up(db,current_user=current_user,payload=payload,ip_address=ip(r))
@follow_router.get("/{id}",response_model=FollowUpItem)
def fg(id:UUID,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):x=s._fu(db,id);s._access_fu(db,current_user,x);return s._fu_item(x)
@follow_router.put("/{id}",response_model=FollowUpItem)
def fu(id:UUID,payload:FollowUpUpdate,r:Request,db:Session=Depends(get_db),current_user:User=Depends(require_csrf)):return s.update_follow_up(db,current_user=current_user,id=id,payload=payload,ip_address=ip(r))
@follow_router.post("/{id}/complete",response_model=FollowUpItem)
def fcomp(id:UUID,r:Request,db:Session=Depends(get_db),current_user:User=Depends(require_csrf)):return s.transition_follow_up(db,current_user=current_user,id=id,action="completed",ip_address=ip(r))
@follow_router.post("/{id}/cancel",response_model=FollowUpItem)
def fcan(id:UUID,r:Request,db:Session=Depends(get_db),current_user:User=Depends(require_csrf)):return s.transition_follow_up(db,current_user=current_user,id=id,action="cancelled",ip_address=ip(r))
@follow_router.post("/{id}/reschedule",response_model=FollowUpItem)
def fres(id:UUID,payload:Reschedule,r:Request,db:Session=Depends(get_db),current_user:User=Depends(require_csrf)):return s.transition_follow_up(db,current_user=current_user,id=id,action="rescheduled",payload=payload,ip_address=ip(r))
@follow_router.get("/{id}/history",response_model=list[History])
def fh(id:UUID,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):return s.follow_history(db,current_user=current_user,id=id)
@activity_router.get("",response_model=ActivityPage)
def al(activity_type:ActivityType|None=None,assigned_user_id:UUID|None=None,page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):return s.list_activities(db,current_user=current_user,activity_type=activity_type,assigned_user_id=assigned_user_id,page=page,page_size=page_size)
@activity_router.post("",response_model=ActivityItem,status_code=status.HTTP_201_CREATED)
def ac(payload:ActivityCreate,r:Request,db:Session=Depends(get_db),current_user:User=Depends(require_csrf)):return s.create_activity(db,current_user=current_user,payload=payload,ip_address=ip(r))
@activity_router.get("/{id}",response_model=ActivityItem)
def ag(id:UUID,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):return s.get_activity(db,current_user=current_user,id=id)
@activity_router.put("/{id}",response_model=ActivityItem)
def au(id:UUID,payload:ActivityUpdate,r:Request,db:Session=Depends(get_db),current_user:User=Depends(require_csrf)):return s.update_activity(db,current_user=current_user,id=id,payload=payload,ip_address=ip(r))
@activity_router.get("/{id}/history",response_model=list[History])
def ah(id:UUID,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):x=s._activity(db,id);s._target(db,current_user,x.customer_id,x.lead_id,x.opportunity_id);return s._history(db,"activity",id)

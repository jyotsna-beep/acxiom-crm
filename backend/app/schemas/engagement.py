from datetime import date, datetime
from math import ceil
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.schemas.customer import CustomerOwnerResponse

FollowUpStatus=Literal["planned","completed","missed","cancelled"]
FollowUpType=Literal["call","meeting","email","task"]
ActivityType=Literal["call","meeting","email","task"]
class TargetBase(BaseModel):
 model_config=ConfigDict(extra="forbid")
 customer_id:UUID|None=None; lead_id:UUID|None=None; opportunity_id:UUID|None=None
 @model_validator(mode="after")
 def one_target(self):
  if sum(x is not None for x in (self.customer_id,self.lead_id,self.opportunity_id))!=1: raise ValueError("Exactly one related record is required.")
  return self
class FollowUpCreate(TargetBase):
 follow_up_date:date; follow_up_type:FollowUpType; subject:str=Field(min_length=1,max_length=200); notes:str|None=Field(None,max_length=2000); assigned_user_id:UUID|None=None
class FollowUpUpdate(BaseModel):
 model_config=ConfigDict(extra="forbid")
 customer_id:UUID|None=None; lead_id:UUID|None=None; opportunity_id:UUID|None=None
 follow_up_date:date|None=None; follow_up_type:FollowUpType|None=None; subject:str|None=Field(None,min_length=1,max_length=200); notes:str|None=Field(None,max_length=2000); assigned_user_id:UUID|None=None
class Reschedule(BaseModel):
 model_config=ConfigDict(extra="forbid")
 follow_up_date:date
class Assigned(CustomerOwnerResponse): pass
class FollowUpItem(BaseModel):
 id:UUID; subject:str; follow_up_date:date; follow_up_type:FollowUpType; status:FollowUpStatus; assigned_user:Assigned; customer_id:UUID|None; lead_id:UUID|None; opportunity_id:UUID|None; completed_at:datetime|None; notes:str|None
class FollowUpPage(BaseModel):
 items:list[FollowUpItem];page:int;page_size:int;total:int;total_pages:int
 @classmethod
 def create(cls,**x): x["total_pages"]=ceil(x["total"]/x["page_size"]) if x["total"] else 0;return cls(**x)
class History(BaseModel): id:UUID;action:str;result:str;created_at:str;actor_id:UUID|None;details:str|None
class ActivityCreate(TargetBase):
 activity_type:ActivityType; subject:str=Field(min_length=1,max_length=200); description:str|None=Field(None,max_length=2000); activity_date:datetime; assigned_user_id:UUID|None=None
class ActivityUpdate(BaseModel):
 model_config=ConfigDict(extra="forbid")
 customer_id:UUID|None=None; lead_id:UUID|None=None; opportunity_id:UUID|None=None
 activity_type:ActivityType|None=None; subject:str|None=Field(None,min_length=1,max_length=200); description:str|None=Field(None,max_length=2000); activity_date:datetime|None=None; assigned_user_id:UUID|None=None
class ActivityItem(BaseModel):
 id:UUID;activity_type:ActivityType;subject:str;description:str|None;activity_date:datetime;status:str;assigned_user:Assigned;customer_id:UUID|None;lead_id:UUID|None;opportunity_id:UUID|None
class ActivityPage(BaseModel):
 items:list[ActivityItem];page:int;page_size:int;total:int;total_pages:int
 @classmethod
 def create(cls,**x): x["total_pages"]=ceil(x["total"]/x["page_size"]) if x["total"] else 0;return cls(**x)

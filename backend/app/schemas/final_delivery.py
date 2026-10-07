from decimal import Decimal
from math import ceil
from uuid import UUID
from pydantic import BaseModel,EmailStr
class Dashboard(BaseModel):
 total_customers:int;active_customers:int;total_leads:int;leads_by_status:dict[str,int];total_opportunities:int;active_opportunities:int;won_opportunities:int;lost_opportunities:int;pipeline_value:Decimal;weighted_pipeline:Decimal;upcoming_follow_ups:int;overdue_follow_ups:int
class AuditItem(BaseModel):id:UUID;user:EmailStr|None;action:str;module:str;record_id:str|None;result:str;details:str|None;created_at:str
class AuditPage(BaseModel):
 items:list[AuditItem];page:int;page_size:int;total:int;total_pages:int
 @classmethod
 def create(cls,*,items,page,page_size,total):return cls(items=items,page=page,page_size=page_size,total=total,total_pages=ceil(total/page_size)if total else 0)
class ReportPage(BaseModel):report_type:str;formula:str|None=None;items:list[dict];page:int;page_size:int;total:int;total_pages:int

from datetime import date
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import func,select
from sqlalchemy.orm import Session,joinedload
from app.models.customer import Customer
from app.models.lead import Lead
from app.models.opportunity import Opportunity
from app.models.follow_up import FollowUp
from app.models.activity import Activity
from app.models.audit_log import AuditLog
from app.models.user import User
from app.policies.authorization import authorized_user_ids
from app.schemas.final_delivery import *
def _scope(stmt,model,db,user,column):
 ids=authorized_user_ids(db,user);return stmt if ids is None else stmt.where(column.in_(ids))
def dashboard(db,user):
 ids=authorized_user_ids(db,user); where=lambda col: [] if ids is None else [col.in_(ids)]
 customers=lambda extra=[]:db.scalar(select(func.count()).select_from(Customer).where(*where(Customer.owner_id),*extra))or 0
 leads=lambda extra=[]:db.scalar(select(func.count()).select_from(Lead).where(*where(Lead.owner_id),*extra))or 0
 opp=lambda extra=[]:db.scalar(select(func.count()).select_from(Opportunity).where(*where(Opportunity.owner_id),*extra))or 0
 lead_status={x:leads([Lead.status==x])for x in ("new","contacted","qualified","unqualified","converted","lost")}
 active=[Opportunity.stage.in_(["qualification","proposal","negotiation"])]
 pipeline=db.scalar(select(func.coalesce(func.sum(Opportunity.amount),0)).where(*where(Opportunity.owner_id),*active))or 0
 weighted=db.scalar(select(func.coalesce(func.sum(Opportunity.amount*Opportunity.probability/100),0)).where(*where(Opportunity.owner_id),*active))or 0
 follow_where=[] if ids is None else [FollowUp.assigned_user_id.in_(ids)]
 return Dashboard(total_customers=customers(),active_customers=customers([Customer.status=="active"]),total_leads=leads(),leads_by_status=lead_status,total_opportunities=opp(),active_opportunities=opp(active),won_opportunities=opp([Opportunity.stage=="won"]),lost_opportunities=opp([Opportunity.stage=="lost"]),pipeline_value=Decimal(pipeline),weighted_pipeline=Decimal(weighted),upcoming_follow_ups=db.scalar(select(func.count()).select_from(FollowUp).where(*follow_where,FollowUp.status=="planned",FollowUp.follow_up_date>=date.today()))or 0,overdue_follow_ups=db.scalar(select(func.count()).select_from(FollowUp).where(*follow_where,FollowUp.status=="planned",FollowUp.follow_up_date<date.today()))or 0)
def audit_list(db,*,user_id,module,action,result,page,page_size):
 stmt=select(AuditLog).options(joinedload(AuditLog.user))
 if user_id:stmt=stmt.where(AuditLog.user_id==user_id)
 if module:stmt=stmt.where(AuditLog.entity_name==module)
 if action:stmt=stmt.where(AuditLog.action==action)
 if result:stmt=stmt.where(AuditLog.result==result)
 total=db.scalar(select(func.count()).select_from(stmt.subquery()))or 0;rows=db.scalars(stmt.order_by(AuditLog.created_at.desc()).offset((page-1)*page_size).limit(page_size)).unique().all()
 return AuditPage.create(items=[AuditItem(id=x.id,user=x.user.email if x.user else None,action=x.action,module=x.entity_name,record_id=x.record_id,result=x.result,details=x.details,created_at=x.created_at.isoformat())for x in rows],page=page,page_size=page_size,total=total)
def reports(db,user,report_type,page,page_size):
 ids=authorized_user_ids(db,user);owner=lambda col:[]if ids is None else[col.in_(ids)]
 if report_type=="customers":rows=[{"name":x.name,"status":x.status,"owner_id":str(x.owner_id)if x.owner_id else None}for x in db.scalars(select(Customer).where(*owner(Customer.owner_id)).offset((page-1)*page_size).limit(page_size))];total=db.scalar(select(func.count()).select_from(Customer).where(*owner(Customer.owner_id)))or 0
 elif report_type=="leads":rows=[{"name":x.name,"status":x.status,"source":x.source,"owner_id":str(x.owner_id)if x.owner_id else None}for x in db.scalars(select(Lead).where(*owner(Lead.owner_id)).offset((page-1)*page_size).limit(page_size))];total=db.scalar(select(func.count()).select_from(Lead).where(*owner(Lead.owner_id)))or 0
 elif report_type in {"opportunities","pipeline"}:rows=[{"name":x.name,"stage":x.stage,"amount":str(x.amount),"probability":str(x.probability)}for x in db.scalars(select(Opportunity).where(*owner(Opportunity.owner_id)).offset((page-1)*page_size).limit(page_size))];total=db.scalar(select(func.count()).select_from(Opportunity).where(*owner(Opportunity.owner_id)))or 0
 elif report_type=="follow_ups":rows=[{"subject":x.subject,"status":x.status,"date":str(x.follow_up_date)}for x in db.scalars(select(FollowUp).where(*([]if ids is None else[FollowUp.assigned_user_id.in_(ids)])).offset((page-1)*page_size).limit(page_size))];total=len(rows)
 elif report_type=="conversion":
  total=db.scalar(select(func.count()).select_from(Lead).where(*owner(Lead.owner_id)))or 0;converted=db.scalar(select(func.count()).select_from(Lead).where(*owner(Lead.owner_id),Lead.status=="converted"))or 0;rows=[{"total_leads":total,"converted_leads":converted,"conversion_rate":round(converted/total*100,2)if total else 0}]
 else:rows=[];total=0
 return ReportPage(report_type=report_type,formula="converted leads / total leads"if report_type=="conversion"else None,items=rows,page=page,page_size=page_size,total=total,total_pages=(total+page_size-1)//page_size if total else 0)

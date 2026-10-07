from typing import Literal
from uuid import UUID
from fastapi import APIRouter,Depends,Query
from sqlalchemy.orm import Session
from app.api.deps import get_current_user,require_roles
from app.core.database import get_db
from app.models.user import User
from app.policies.authorization import RoleName
from app.schemas.final_delivery import Dashboard,AuditPage,ReportPage
from app.services.final_delivery_service import dashboard,audit_list,reports
router=APIRouter(tags=["final delivery"])
@router.get("/api/dashboard",response_model=Dashboard)
def dash(db:Session=Depends(get_db),user:User=Depends(get_current_user)):return dashboard(db,user)
@router.get("/api/audit-logs",response_model=AuditPage)
def audits(user_id:UUID|None=None,module:str|None=None,action:str|None=None,result:str|None=None,page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),db:Session=Depends(get_db),_:User=Depends(require_roles(RoleName.ADMIN))):return audit_list(db,user_id=user_id,module=module,action=action,result=result,page=page,page_size=page_size)
@router.get("/api/reports/{report_type}",response_model=ReportPage)
def report(report_type:Literal["customers","leads","follow_ups","opportunities","pipeline","conversion","user_activity","audit"],page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),db:Session=Depends(get_db),user:User=Depends(get_current_user)):return reports(db,user,report_type,page,page_size)

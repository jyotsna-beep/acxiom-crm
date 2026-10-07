from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, require_csrf
from app.core.database import get_db
from app.models.user import User
from app.schemas.opportunity import OpportunityCreate, OpportunityHistoryItem, OpportunityOwnerResponse, OpportunityPage, OpportunityResponse, OpportunityStageChange, OpportunityUpdate
from app.services.opportunity_service import change_stage, create_opportunity, get_opportunity, list_opportunities, list_owners, opportunity_history, update_opportunity
router=APIRouter(prefix="/api/opportunities",tags=["opportunities"])
def _ip(r): return r.client.host if r.client else None
@router.get("",response_model=OpportunityPage)
def listing(search:str|None=Query(None,max_length=150),stage:Literal["qualification","proposal","negotiation","won","lost"]|None=None,owner_id:UUID|None=None,customer_id:UUID|None=None,page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),sort_by:Literal["name","stage","amount","probability","expected_close_date","created_at","opportunity_code"]="name",sort_order:Literal["asc","desc"]="asc",db:Session=Depends(get_db),current_user:User=Depends(get_current_user)): return list_opportunities(db,current_user=current_user,search=search,stage=stage,owner_id=owner_id,customer_id=customer_id,page=page,page_size=page_size,sort_by=sort_by,sort_order=sort_order)
@router.post("",response_model=OpportunityResponse,status_code=status.HTTP_201_CREATED)
def create(payload:OpportunityCreate,request:Request,db:Session=Depends(get_db),current_user:User=Depends(require_csrf)): return create_opportunity(db,current_user=current_user,payload=payload,ip_address=_ip(request))
@router.get("/owners",response_model=list[OpportunityOwnerResponse])
def owners(db:Session=Depends(get_db),current_user:User=Depends(get_current_user)): return list_owners(db,current_user=current_user)
@router.get("/{opportunity_id}",response_model=OpportunityResponse)
def get_one(opportunity_id:UUID,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)): return get_opportunity(db,current_user=current_user,opportunity_id=opportunity_id)
@router.put("/{opportunity_id}",response_model=OpportunityResponse)
def update(opportunity_id:UUID,payload:OpportunityUpdate,request:Request,db:Session=Depends(get_db),current_user:User=Depends(require_csrf)): return update_opportunity(db,current_user=current_user,opportunity_id=opportunity_id,payload=payload,ip_address=_ip(request))
@router.post("/{opportunity_id}/stage",response_model=OpportunityResponse)
def stage(opportunity_id:UUID,payload:OpportunityStageChange,request:Request,db:Session=Depends(get_db),current_user:User=Depends(require_csrf)): return change_stage(db,current_user=current_user,opportunity_id=opportunity_id,payload=payload,ip_address=_ip(request))
@router.get("/{opportunity_id}/history",response_model=list[OpportunityHistoryItem])
def history(opportunity_id:UUID,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)): return opportunity_history(db,current_user=current_user,opportunity_id=opportunity_id)

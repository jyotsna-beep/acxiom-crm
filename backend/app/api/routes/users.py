from typing import Literal
from uuid import UUID
from fastapi import APIRouter,Depends,Query,Request,status
from sqlalchemy.orm import Session
from app.api.deps import require_csrf,require_roles
from app.core.database import get_db
from app.models.user import User
from app.policies.authorization import RoleName
from app.schemas.user_management import *
from app.services import user_management_service as s
router=APIRouter(prefix="/api/users",tags=["users"])
def ip(r):return r.client.host if r.client else None
Admin=Depends(require_roles(RoleName.ADMIN))
@router.get("",response_model=UserPage)
def listing(search:str|None=Query(None,max_length=150),role:RoleValue|None=None,is_active:bool|None=None,manager_id:UUID|None=None,page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),sort_by:Literal["name","email","username","created_at"]="name",sort_order:Literal["asc","desc"]="asc",db:Session=Depends(get_db),admin:User=Admin):return s.list_users(db,search=search,role=role,is_active=is_active,manager_id=manager_id,page=page,page_size=page_size,sort_by=sort_by,sort_order=sort_order)
@router.post("",response_model=UserItem,status_code=status.HTTP_201_CREATED)
def create(payload:UserCreate,r:Request,db:Session=Depends(get_db),admin:User=Admin,_:User=Depends(require_csrf)):return s.create_user(db,admin=admin,payload=payload,ip_address=ip(r))
@router.get("/{id}",response_model=UserItem)
def get(id:UUID,db:Session=Depends(get_db),admin:User=Admin):return s._item(s._get(db,id))
@router.put("/{id}",response_model=UserItem)
def update(id:UUID,payload:UserUpdate,r:Request,db:Session=Depends(get_db),admin:User=Admin,_:User=Depends(require_csrf)):return s.update_user(db,admin=admin,id=id,payload=payload,ip_address=ip(r))
@router.post("/{id}/activate",response_model=UserItem)
def activate(id:UUID,r:Request,db:Session=Depends(get_db),admin:User=Admin,_:User=Depends(require_csrf)):return s.set_active(db,admin=admin,id=id,active=True,ip_address=ip(r))
@router.post("/{id}/deactivate",response_model=UserItem)
def deactivate(id:UUID,r:Request,db:Session=Depends(get_db),admin:User=Admin,_:User=Depends(require_csrf)):return s.set_active(db,admin=admin,id=id,active=False,ip_address=ip(r))
@router.post("/{id}/reset-password",status_code=status.HTTP_204_NO_CONTENT)
def reset(id:UUID,payload:PasswordReset,r:Request,db:Session=Depends(get_db),admin:User=Admin,_:User=Depends(require_csrf)):s.reset_password(db,admin=admin,id=id,payload=payload,ip_address=ip(r))

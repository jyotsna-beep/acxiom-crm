from math import ceil
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

RoleValue=Literal["Admin","Manager","Sales Executive"]
class UserManager(BaseModel): id:UUID;username:str|None;email:EmailStr
class UserItem(BaseModel):
 id:UUID;name:str;username:str|None;email:EmailStr;role:RoleValue;is_active:bool;manager:UserManager|None;created_at:str;updated_at:str
class UserPage(BaseModel):
 items:list[UserItem];page:int;page_size:int;total:int;total_pages:int
 @classmethod
 def create(cls,*,items,page,page_size,total):return cls(items=items,page=page,page_size=page_size,total=total,total_pages=ceil(total/page_size)if total else 0)
class UserCreate(BaseModel):
 model_config=ConfigDict(extra="forbid")
 name:str=Field(min_length=1,max_length=150);username:str=Field(min_length=3,max_length=100);email:EmailStr;password:str=Field(min_length=8,max_length=256);role:RoleValue;manager_id:UUID|None=None;is_active:bool=True
 @field_validator("name","username")
 @classmethod
 def trim(cls,v):
  v=v.strip()
  if not v:raise ValueError("This field is required.")
  return v
class UserUpdate(BaseModel):
 model_config=ConfigDict(extra="forbid")
 name:str|None=Field(None,min_length=1,max_length=150);username:str|None=Field(None,min_length=3,max_length=100);email:EmailStr|None=None;role:RoleValue|None=None;manager_id:UUID|None=None
class PasswordReset(BaseModel):
 model_config=ConfigDict(extra="forbid")
 password:str=Field(min_length=8,max_length=256)

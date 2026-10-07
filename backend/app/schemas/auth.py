from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    identity: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    username: str | None = Field(default=None, min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=256)


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: EmailStr
    username: str | None
    role: str
    is_active: bool


class AuthResponse(BaseModel):
    user: CurrentUserResponse


class RegistrationResponse(BaseModel):
    message: str

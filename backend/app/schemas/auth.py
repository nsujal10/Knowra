from pydantic import BaseModel, EmailStr
from uuid import UUID
from typing import List

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    organization_name: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class CurrentUserContext(BaseModel):
    user_id: UUID
    organization_id: UUID
    role_code: str
    permissions: List[str]

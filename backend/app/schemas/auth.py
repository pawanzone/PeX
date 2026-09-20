"""Authentication, Personas, and Session Schemas."""
from typing import Optional, List
from pydantic import BaseModel
from app.schemas.approval import UserRole

class UserPersona(BaseModel):
    user_id: str
    name: str
    email: str
    role: UserRole
    title: str
    department: str
    avatar_initials: str
    badge_color: str
    max_approval_amount: float
    is_demo_active: bool = False

class LoginRequest(BaseModel):
    user_id: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPersona

from typing import Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime

# --- Token Schemas ---

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None

# --- User Schemas ---

class UserBase(BaseModel):
    email: Optional[EmailStr] = None

class UserCreate(UserBase):
    email: EmailStr
    password: str

class UserUpdate(UserBase):
    password: Optional[str] = None

class UserOut(UserBase):
    id: int
    email: EmailStr

    class Config:
        from_attributes = True

# --- Auth ---

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# --- Project Schemas ---

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    tech_stack: str

class ProjectCreate(ProjectBase):
    pass

class ProjectOut(ProjectBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

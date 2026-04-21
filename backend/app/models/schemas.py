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

# --- Job Schemas ---

class JobOut(BaseModel):
    id: int
    project_id: int
    status: str
    source_version: Optional[str] = None
    target_version: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    project_name: Optional[str] = None # Added via join

    class Config:
        from_attributes = True

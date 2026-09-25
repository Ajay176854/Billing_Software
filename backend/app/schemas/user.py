"""
User schemas — request/response models for authentication and user management.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# --- Auth ---
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


# --- User CRUD ---
class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[str] = None
    password: str = Field(..., min_length=6)
    role: str = Field(default="staff", pattern="^(admin|staff|inventory)$")


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = None
    role: Optional[str] = Field(None, pattern="^(admin|staff|inventory)$")
    status: Optional[str] = Field(None, pattern="^(active|inactive)$")


class PasswordReset(BaseModel):
    new_password: str = Field(..., min_length=6)


class UserResponse(BaseModel):
    id: int
    name: str
    username: str
    email: Optional[str] = None
    role: str
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

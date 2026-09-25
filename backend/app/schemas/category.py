"""
Category schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    prefix: Optional[str] = Field(None, max_length=10)


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    prefix: Optional[str] = Field(None, max_length=10)
    status: Optional[str] = Field(None, pattern="^(active|inactive)$")


class CategoryResponse(BaseModel):
    id: int
    name: str
    prefix: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

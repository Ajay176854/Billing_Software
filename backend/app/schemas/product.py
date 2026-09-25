"""
Product schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ProductCreate(BaseModel):
    barcode: Optional[str] = Field(None, max_length=50)
    sku: Optional[str] = Field(None, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    category_id: Optional[int] = None
    purchase_price: float = Field(default=0.0, ge=0)
    selling_price: float = Field(..., ge=0)
    tax_rate: float = Field(default=0.0, ge=0, le=100)
    stock_qty: int = Field(default=0, ge=0)
    reorder_level: int = Field(default=10, ge=0)
    unit: str = Field(default="pcs", max_length=20)


class ProductUpdate(BaseModel):
    barcode: Optional[str] = Field(None, max_length=50)
    sku: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    category_id: Optional[int] = None
    purchase_price: Optional[float] = Field(None, ge=0)
    selling_price: Optional[float] = Field(None, ge=0)
    tax_rate: Optional[float] = Field(None, ge=0, le=100)
    reorder_level: Optional[int] = Field(None, ge=0)
    unit: Optional[str] = Field(None, max_length=20)
    status: Optional[str] = Field(None, pattern="^(active|inactive)$")


class ProductResponse(BaseModel):
    id: int
    barcode: Optional[str] = None
    sku: Optional[str] = None
    name: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    purchase_price: float
    selling_price: float
    tax_rate: float
    stock_qty: int
    reorder_level: int
    unit: str
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

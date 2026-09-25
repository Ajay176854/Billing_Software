"""
Sale / Billing schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# --- Cart / Billing Request ---
class CartItem(BaseModel):
    product_id: int
    quantity: int = Field(..., ge=1)
    discount: float = Field(default=0.0, ge=0)  # item-level discount amount


class BillRequest(BaseModel):
    items: List[CartItem] = Field(..., min_length=1)
    payment_method: str = Field(default="cash", pattern="^(cash|upi|card)$")
    bill_discount: float = Field(default=0.0, ge=0)  # bill-level discount amount
    notes: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_place: Optional[str] = None
    customer_email: Optional[str] = None


# --- Sale Response ---
class SaleItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    product_barcode: Optional[str] = None
    quantity: int
    unit_price: float
    discount: float
    tax_rate: float
    tax: float
    subtotal: float

    class Config:
        from_attributes = True


class SaleResponse(BaseModel):
    id: int
    invoice_no: str
    user_id: int
    user_name: Optional[str] = None
    subtotal: float
    discount: float
    tax: float
    total: float
    payment_method: str
    status: str
    notes: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_place: Optional[str] = None
    customer_email: Optional[str] = None
    items: List[SaleItemResponse] = []
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SaleListResponse(BaseModel):
    id: int
    invoice_no: str
    user_name: Optional[str] = None
    customer_name: Optional[str] = None
    total: float
    payment_method: str
    status: str
    items_count: int = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

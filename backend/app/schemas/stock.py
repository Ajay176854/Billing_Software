"""
Stock / Inventory schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class StockInRequest(BaseModel):
    product_id: int
    quantity: int = Field(..., ge=1)
    reason: Optional[str] = "Stock purchase"


class StockAdjustRequest(BaseModel):
    product_id: int
    quantity: int  # positive to add, negative to remove
    reason: str = Field(..., min_length=1)


class StockTransactionResponse(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    product_barcode: Optional[str] = None
    type: str
    quantity: int
    reference_id: Optional[str] = None
    reason: Optional[str] = None
    user_id: int
    user_name: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

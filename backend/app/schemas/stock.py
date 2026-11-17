"""
Stock / Inventory schemas.
"""
from pydantic import BaseModel, Field, field_serializer
from typing import Optional
from datetime import datetime, timezone


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

    @field_serializer("created_at")
    def serialize_created_at(self, dt: Optional[datetime], _info):
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    class Config:
        from_attributes = True

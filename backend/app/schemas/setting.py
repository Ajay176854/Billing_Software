"""
Setting schemas.
"""
from pydantic import BaseModel
from typing import Optional, Dict


class SettingUpdate(BaseModel):
    value: Optional[str] = None


class SettingResponse(BaseModel):
    key: str
    value: Optional[str] = None

    class Config:
        from_attributes = True


class BulkSettingsUpdate(BaseModel):
    settings: Dict[str, str]


class StoreProfile(BaseModel):
    store_name: str = ""
    store_address: str = ""
    store_phone: str = ""
    store_email: str = ""
    store_gst: str = ""
    invoice_prefix: str = "INV"
    currency_symbol: str = "₹"

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
    currency_symbol: str = "Rs."
    receipt_width: str = "58mm"
    label_size: str = "50x30mm"
    printer_model: str = "DEV 632-L58P (2-in-1 Receipt + Label)"
    scanner_model: str = "Helett HT20 (USB)"
    auto_print: str = "false"


"""
Settings router — store configuration management.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict

from app.database import get_db
from app.auth import require_role, get_current_user
from app.models.setting import Setting
from app.schemas.setting import BulkSettingsUpdate, StoreProfile

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("", response_model=Dict[str, str])
def get_all_settings(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Get all settings as key-value pairs."""
    settings = db.query(Setting).all()
    return {s.key: s.value or "" for s in settings}


@router.get("/store-profile", response_model=StoreProfile)
def get_store_profile(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Get store profile settings."""
    settings = db.query(Setting).all()
    settings_dict = {s.key: s.value or "" for s in settings}
    return StoreProfile(
        store_name=settings_dict.get("store_name", ""),
        store_address=settings_dict.get("store_address", ""),
        store_phone=settings_dict.get("store_phone", ""),
        store_email=settings_dict.get("store_email", ""),
        store_gst=settings_dict.get("store_gst", ""),
        invoice_prefix=settings_dict.get("invoice_prefix", "INV"),
        currency_symbol=settings_dict.get("currency_symbol", "₹"),
    )


@router.put("", response_model=Dict[str, str])
def update_settings(
    data: BulkSettingsUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """Update multiple settings at once."""
    for key, value in data.settings.items():
        setting = db.query(Setting).filter(Setting.key == key).first()
        if setting:
            setting.value = value
        else:
            db.add(Setting(key=key, value=value))

    db.commit()

    # Return updated settings
    settings = db.query(Setting).all()
    return {s.key: s.value or "" for s in settings}

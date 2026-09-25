"""
Billing Software Backend - Application Configuration
"""
from pydantic_settings import BaseSettings
from pathlib import Path
import secrets


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Retail Billing & Inventory Management"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql://postgres.obgjwzsthcsculzmikvp:Ajaiashwa%402004@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres"

    # JWT Authentication
    SECRET_KEY: str = "729a4a7538a7c2980c58e657a79a6136d4df6a929fb0740632b6946e3ed9fb71"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # Default Admin
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "admin123"
    DEFAULT_ADMIN_NAME: str = "Administrator"

    # Store Defaults
    STORE_NAME: str = "My Retail Store"
    STORE_ADDRESS: str = ""
    STORE_PHONE: str = ""
    STORE_GST: str = ""
    INVOICE_PREFIX: str = "INV"

    # Currency
    CURRENCY_SYMBOL: str = "₹"
    CURRENCY_CODE: str = "INR"

    class Config:
        extra = "allow"


settings = Settings()

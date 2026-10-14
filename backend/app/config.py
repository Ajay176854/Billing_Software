"""
Billing Software Backend - Application Configuration
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Retail Billing & Inventory Management"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database - Default to local SQLite, override in .env for production
    # On Vercel, the filesystem is read-only except for /tmp.
    DATABASE_URL: str = "sqlite:////tmp/billing.db"
    
    # Redis Cache - Default to local Redis
    REDIS_URL: str = "redis://localhost:6379"

    # JWT Authentication - Override in .env for production
    SECRET_KEY: str = "729a4a7538a7c2980c58e657a79a6136d4df6a929fb0740632b6946e3ed9fb71"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # CORS
    ALLOWED_ORIGINS: str = "*"

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
        import sys, os
        from pathlib import Path
        # Look in sys._MEIPASS (PyInstaller bundle), executable directory, backend dir, or current dir
        _search_dirs = [
            getattr(sys, '_MEIPASS', None),
            Path(sys.executable).parent if getattr(sys, 'frozen', False) else None,
            Path(__file__).resolve().parent.parent,
            Path.cwd(),
        ]
        _found_env = ".env"
        for _d in _search_dirs:
            if _d:
                _candidate = Path(_d) / ".env"
                if _candidate.exists():
                    _found_env = str(_candidate)
                    break

        env_file = _found_env
        extra = "allow"


settings = Settings()

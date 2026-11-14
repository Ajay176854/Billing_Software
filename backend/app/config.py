"""
Billing Software Backend - Application Configuration
"""
import sys
import os
from pathlib import Path
from pydantic_settings import BaseSettings


def get_current_app_version() -> str:
    """
    Dynamically resolve the installed version:
    1. Check version.txt in executable directory
    2. Check git describe tags if running in repository
    3. Fallback to latest known release
    """
    # 1. Check version.txt next to executable or in bundle
    try:
        import sys
        if getattr(sys, "frozen", False):
            base_dir = Path(sys.executable).parent
            # Check external version.txt next to executable first (updated by updater batch)
            ext_v = base_dir / "version.txt"
            if ext_v.exists():
                v = ext_v.read_text(encoding="utf-8").strip()
                if v:
                    return v.lstrip("v")

            # Check bundled MEIPASS
            mei_dir = getattr(sys, "_MEIPASS", None)
            if mei_dir and (Path(mei_dir) / "version.txt").exists():
                v = (Path(mei_dir) / "version.txt").read_text(encoding="utf-8").strip()
                if v:
                    return v.lstrip("v")
        else:
            base_dir = Path(__file__).resolve().parent.parent.parent
            v_file = base_dir / "version.txt"
            if v_file.exists():
                v = v_file.read_text(encoding="utf-8").strip()
                if v:
                    return v.lstrip("v")
    except Exception:
        pass

    # 2. Dynamic Git Tag resolution (Automatic for new releases)
    try:
        import subprocess
        root_dir = Path(__file__).resolve().parent.parent.parent
        git_tag = subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=str(root_dir),
            text=True,
            stderr=subprocess.DEVNULL
        ).strip().lstrip("v")
        if git_tag:
            return git_tag
    except Exception:
        pass

    return "1.0.4"


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Retail Billing & Inventory Management"
    APP_VERSION: str = get_current_app_version()
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
        import sys
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

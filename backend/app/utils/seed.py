"""
Seed utility — creates default admin and sample categories on first run.
"""
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.category import Category
from app.models.setting import Setting
from app.auth import hash_password
from app.config import settings


def seed_database(db: Session):
    """Seed initial data if the database is empty."""

    # Create default admin user
    admin = db.query(User).filter(User.username == settings.DEFAULT_ADMIN_USERNAME).first()
    if not admin:
        admin = User(
            name=settings.DEFAULT_ADMIN_NAME,
            username=settings.DEFAULT_ADMIN_USERNAME,
            password_hash=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
            role="admin",
            status="active",
        )
        db.add(admin)
        print(f"[OK] Created default admin user: {settings.DEFAULT_ADMIN_USERNAME}")

    # Create default categories
    default_categories = [
        {"name": "Bangle", "prefix": "BGL"},
        {"name": "Anklet", "prefix": "ANK"},
        {"name": "Earring", "prefix": "EAR"},
        {"name": "Necklace", "prefix": "NCK"},
        {"name": "Ring", "prefix": "RNG"},
        {"name": "Bracelet", "prefix": "BRC"},
        {"name": "General", "prefix": "GEN"},
        {"name": "Others", "prefix": "OTH"},
    ]

    for cat_data in default_categories:
        exists = db.query(Category).filter(Category.name == cat_data["name"]).first()
        if not exists:
            db.add(Category(name=cat_data["name"], prefix=cat_data["prefix"]))
        elif not exists.prefix:
            exists.prefix = cat_data["prefix"]

    # Seed default settings
    default_settings = {
        "store_name": settings.STORE_NAME,
        "store_address": settings.STORE_ADDRESS,
        "store_phone": settings.STORE_PHONE,
        "store_gst": settings.STORE_GST,
        "store_email": "",
        "invoice_prefix": settings.INVOICE_PREFIX,
        "currency_symbol": settings.CURRENCY_SYMBOL,
    }

    for key, value in default_settings.items():
        exists = db.query(Setting).filter(Setting.key == key).first()
        if not exists:
            db.add(Setting(key=key, value=value))

    db.commit()
    print("[OK] Database seeded successfully")

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import random

# Import models
from app.database import Base
from app.config import settings
from app.models.user import User
from app.models.category import Category
from app.models.product import Product
from app.models.sale_item import SaleItem
from app.auth import hash_password

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    print("Dropping old tables to make it fresh...")
    Base.metadata.drop_all(engine)
    print("Creating tables in Supabase...")
    Base.metadata.create_all(engine)
    
    db = SessionLocal()
    
    # 1. Create Admin
    if not db.query(User).filter_by(username="moira_admin").first():
        print("Creating admin user...")
        admin = User(
            name="Admin",
            username="moira_admin",
            password_hash=hash_password("MoiraLuxe@2026"),
            role="admin"
        )
        db.add(admin)
        db.commit()

    print("Supabase setup complete! Tables and Admin user created (Production Ready).")
    db.close()

if __name__ == "__main__":
    init_db()

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
    print("Creating tables in Supabase...")
    Base.metadata.create_all(engine)
    
    db = SessionLocal()
    
    # 1. Create Admin
    if not db.query(User).filter_by(username="admin").first():
        print("Creating admin user...")
        admin = User(
            name="Admin",
            username="admin",
            password=hash_password("admin123"),
            role="admin"
        )
        db.add(admin)
        db.commit()

    # 2. Create Categories
    if db.query(Category).count() == 0:
        print("Adding dummy categories...")
        categories = ["Electronics", "Clothing", "Groceries", "Beverages", "Home & Kitchen"]
        for c in categories:
            db.add(Category(name=c, prefix=c[:3].upper()))
        db.commit()

    # 3. Create Products
    if db.query(Product).count() == 0:
        print("Adding dummy products...")
        cats = db.query(Category).all()
        products = [
            {"name": "Wireless Mouse", "price": 499.00, "qty": 50, "cat": cats[0].id, "reorder": 10},
            {"name": "Mechanical Keyboard", "price": 1999.00, "qty": 30, "cat": cats[0].id, "reorder": 5},
            {"name": "Cotton T-Shirt", "price": 399.00, "qty": 100, "cat": cats[1].id, "reorder": 20},
            {"name": "Denim Jeans", "price": 999.00, "qty": 40, "cat": cats[1].id, "reorder": 10},
            {"name": "Basmati Rice 5kg", "price": 450.00, "qty": 20, "cat": cats[2].id, "reorder": 5},
            {"name": "Green Tea Bags", "price": 150.00, "qty": 60, "cat": cats[3].id, "reorder": 15},
            {"name": "Coffee Jar 200g", "price": 280.00, "qty": 35, "cat": cats[3].id, "reorder": 10},
            {"name": "Non-Stick Pan", "price": 850.00, "qty": 15, "cat": cats[4].id, "reorder": 5},
            {"name": "Ceramic Mug", "price": 120.00, "qty": 80, "cat": cats[4].id, "reorder": 20},
        ]
        for p in products:
            prod = Product(
                name=p["name"],
                category_id=p["cat"],
                barcode=f"1000{random.randint(100,999)}",
                purchase_price=p["price"] * 0.7,
                selling_price=p["price"],
                stock_qty=p["qty"],
                reorder_level=p["reorder"]
            )
            db.add(prod)
        db.commit()

    print("Supabase setup complete! Tables and dummy data created.")
    db.close()

if __name__ == "__main__":
    init_db()

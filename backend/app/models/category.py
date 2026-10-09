"""
Category model — TRD §9 categories table.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    prefix = Column(String(10), nullable=True)  # E.g., BGL for Bangle
    status = Column(String(20), nullable=False, default="active")  # active, inactive
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

"""
Setting model — TRD §9 settings table.
Key-value store for application and store configuration.
"""
from sqlalchemy import Column, Integer, String
from app.database import Base


class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(String(500), nullable=True)

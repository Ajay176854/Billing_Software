"""
StockTransaction model — TRD §9 stock_transactions table.
Audit trail for every stock-changing event.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class StockTransaction(Base):
    __tablename__ = "stock_transactions"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    type = Column(String(30), nullable=False)  # STOCK_IN, SALE, ADJUSTMENT, RETURN
    quantity = Column(Integer, nullable=False)  # positive for in, negative for out
    reference_id = Column(String(50), nullable=True)  # e.g., sale invoice_no
    reason = Column(String(255), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    product = relationship("Product", lazy="joined")
    user = relationship("User", lazy="joined")

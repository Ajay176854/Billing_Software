"""
Inventory Service — stock-in, adjustment, and queries.
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.product import Product
from app.models.stock_transaction import StockTransaction


def stock_in(db: Session, product_id: int, quantity: int, user_id: int, reason: str = "Stock purchase") -> Product:
    """Add stock to a product (TRD §6.4)."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.stock_qty += quantity

    txn = StockTransaction(
        product_id=product.id,
        type="STOCK_IN",
        quantity=quantity,
        reason=reason,
        user_id=user_id,
    )
    db.add(txn)
    db.commit()
    db.refresh(product)
    return product


def adjust_stock(db: Session, product_id: int, quantity: int, user_id: int, reason: str) -> Product:
    """
    Manual stock adjustment (TRD §6.4).
    quantity can be positive (add) or negative (remove).
    BR-02: Cannot reduce below zero unless admin overrides.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    new_qty = product.stock_qty + quantity
    if new_qty < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Adjustment would result in negative stock ({new_qty}). Current: {product.stock_qty}"
        )

    product.stock_qty = new_qty

    txn = StockTransaction(
        product_id=product.id,
        type="ADJUSTMENT",
        quantity=quantity,
        reason=reason,
        user_id=user_id,
    )
    db.add(txn)
    db.commit()
    db.refresh(product)
    return product

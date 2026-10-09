"""
Inventory router — stock-in, adjustments, and stock queries.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models.product import Product
from app.models.stock_transaction import StockTransaction
from app.schemas.stock import StockInRequest, StockAdjustRequest, StockTransactionResponse
from app.schemas.product import ProductResponse
from app.services.inventory_service import stock_in, adjust_stock
from app.routers.products import _product_to_response

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.post("/stock-in", response_model=ProductResponse)
def add_stock(
    data: StockInRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin", "inventory")),
):
    """Add stock to a product."""
    product = stock_in(db, data.product_id, data.quantity, current_user.id, data.reason)
    return _product_to_response(product)


@router.post("/adjust", response_model=ProductResponse)
def adjust(
    data: StockAdjustRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin", "inventory")),
):
    """Manually adjust stock with a reason."""
    product = adjust_stock(db, data.product_id, data.quantity, current_user.id, data.reason)
    return _product_to_response(product)


@router.get("/low-stock", response_model=List[ProductResponse])
def low_stock_products(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Get products below their reorder level."""
    from sqlalchemy.orm import joinedload
    products = db.query(Product).options(joinedload(Product.category)).filter(
        Product.status == "active",
        Product.stock_qty > 0,
        Product.stock_qty <= Product.reorder_level,
    ).order_by(Product.stock_qty).all()
    return [_product_to_response(p) for p in products]


@router.get("/out-of-stock", response_model=List[ProductResponse])
def out_of_stock_products(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Get products with zero stock."""
    from sqlalchemy.orm import joinedload
    products = db.query(Product).options(joinedload(Product.category)).filter(
        Product.status == "active",
        Product.stock_qty == 0,
    ).order_by(Product.name).all()
    return [_product_to_response(p) for p in products]


@router.get("/transactions", response_model=List[StockTransactionResponse])
def stock_transactions(
    product_id: Optional[int] = None,
    type: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get stock transaction history."""
    query = db.query(StockTransaction)

    if product_id:
        query = query.filter(StockTransaction.product_id == product_id)
    if type:
        query = query.filter(StockTransaction.type == type)

    from sqlalchemy.orm import joinedload
    txns = query.options(joinedload(StockTransaction.product), joinedload(StockTransaction.user)
                         ).order_by(StockTransaction.created_at.desc()).limit(limit).all()

    return [
        StockTransactionResponse(
            id=t.id,
            product_id=t.product_id,
            product_name=t.product.name if t.product else None,
            product_barcode=t.product.barcode if t.product else None,
            type=t.type,
            quantity=t.quantity,
            reference_id=t.reference_id,
            reason=t.reason,
            user_id=t.user_id,
            user_name=t.user.name if t.user else None,
            created_at=t.created_at,
        )
        for t in txns
    ]

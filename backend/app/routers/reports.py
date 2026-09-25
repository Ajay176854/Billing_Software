"""
Reports router — dashboard stats and business reports.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.database import get_db
from app.auth import get_current_user
from app.services.report_service import (
    get_dashboard_stats,
    get_sales_by_date_range,
    get_product_sales_report,
    get_itemized_sales_report,
    get_customer_traffic_report,
)

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Get dashboard overview statistics."""
    return get_dashboard_stats(db)

@router.get("/sales-by-date")
def sales_by_date(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get daily sales summary for a date range."""
    if not start_date:
        start = datetime.now(timezone.utc) - timedelta(days=30)
    else:
        start = datetime.fromisoformat(start_date)

    if not end_date:
        end = datetime.now(timezone.utc)
    else:
        end = datetime.fromisoformat(end_date)

    return get_sales_by_date_range(db, start, end)

@router.get("/product-sales")
def product_sales(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get product-wise sales report."""
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    return get_product_sales_report(db, start, end)

@router.get("/itemized-sales")
def itemized_sales(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get detailed line-by-line itemized sales."""
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    return get_itemized_sales_report(db, start, end)

@router.get("/customer-traffic")
def customer_traffic(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get customer traffic report."""
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    return get_customer_traffic_report(db, start, end)


@router.get("/customer-detail")
def customer_detail(
    phone: str = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get full purchase history for a specific customer by phone number."""
    from app.models.sale import Sale
    from app.models.sale_item import SaleItem
    from app.models.product import Product

    sales = db.query(Sale).filter(
        Sale.customer_phone == phone,
        Sale.status == "completed"
    ).order_by(Sale.created_at.desc()).all()

    result = []
    for s in sales:
        items = []
        for item in s.items:
            items.append({
                "product_name": item.product.name if item.product else "Unknown",
                "barcode": item.product.barcode if item.product else None,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "subtotal": item.subtotal,
            })
        result.append({
            "id": s.id,
            "invoice_no": s.invoice_no,
            "total": s.total,
            "payment_method": s.payment_method,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "items": items,
        })

    # Get customer info from first sale
    first = sales[0] if sales else None
    return {
        "name": first.customer_name if first else phone,
        "phone": phone,
        "place": first.customer_place if first else None,
        "email": first.customer_email if first else None,
        "total_visits": len(sales),
        "total_spent": sum(s.total for s in sales),
        "purchases": result,
    }

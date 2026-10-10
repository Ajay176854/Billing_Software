"""
Sales router — sales history, details, and cancellation.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.schemas.sale import SaleResponse, SaleListResponse, SaleItemResponse
from app.services.billing_service import cancel_sale

router = APIRouter(prefix="/sales", tags=["Sales"])


@router.get("", response_model=List[SaleListResponse])
def list_sales(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    payment_method: Optional[str] = None,
    invoice_no: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List sales with filters."""
    query = db.query(Sale)

    if start_date:
        query = query.filter(Sale.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(Sale.created_at <= datetime.fromisoformat(end_date))
    if payment_method:
        query = query.filter(Sale.payment_method == payment_method)
    if invoice_no:
        query = query.filter(Sale.invoice_no.ilike(f"%{invoice_no}%"))
    if status_filter:
        query = query.filter(Sale.status == status_filter)

    from sqlalchemy.orm import joinedload
    sales = query.options(joinedload(Sale.user), joinedload(Sale.items)).order_by(Sale.created_at.desc()).limit(limit).all()

    return [
        SaleListResponse(
            id=s.id,
            invoice_no=s.invoice_no,
            user_name=s.user.name if s.user else None,
            customer_name=s.customer_name,
            total=s.total,
            payment_method=s.payment_method,
            status=s.status,
            items_count=len(s.items),
            created_at=s.created_at,
        )
        for s in sales
    ]


@router.get("/customers/search")
def search_customers(q: str = Query(..., min_length=2), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Search unique customers by phone or name from previous sales."""
    customers = (
        db.query(Sale.customer_phone, Sale.customer_name, Sale.customer_place, Sale.customer_email)
        .filter(Sale.customer_phone.ilike(f"%{q}%") | Sale.customer_name.ilike(f"%{q}%"))
        .filter(Sale.customer_phone.is_not(None))
        .filter(Sale.customer_phone != "")
        .distinct()
        .limit(10)
        .all()
    )

    return [
        {
            "phone": c.customer_phone,
            "name": c.customer_name,
            "place": c.customer_place,
            "email": c.customer_email
        }
        for c in customers
    ]


@router.get("/{sale_id}", response_model=SaleResponse)
def get_sale(sale_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Get detailed sale information with line items."""
    from sqlalchemy.orm import joinedload
    sale = db.query(Sale).options(
        joinedload(Sale.user),
        joinedload(Sale.items).joinedload(SaleItem.product)
    ).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    return SaleResponse(
        id=sale.id,
        invoice_no=sale.invoice_no,
        user_id=sale.user_id,
        user_name=sale.user.name if sale.user else None,
        subtotal=sale.subtotal,
        discount=sale.discount,
        tax=sale.tax,
        total=sale.total,
        payment_method=sale.payment_method,
        status=sale.status,
        notes=sale.notes,
        customer_name=sale.customer_name,
        customer_phone=sale.customer_phone,
        customer_place=sale.customer_place,
        customer_email=sale.customer_email,
        items=[
            SaleItemResponse(
                id=item.id,
                product_id=item.product_id,
                product_name=item.product.name if item.product else None,
                product_barcode=item.product.barcode if item.product else None,
                quantity=item.quantity,
                unit_price=item.unit_price,
                discount=item.discount,
                tax_rate=item.tax_rate,
                tax=item.tax,
                subtotal=item.subtotal,
            )
            for item in sale.items
        ],
        created_at=sale.created_at,
    )


@router.post("/{sale_id}/cancel", response_model=SaleResponse)
def cancel(sale_id: int, db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    """Cancel a completed sale (Admin only). Restores stock per BR-04."""
    sale = cancel_sale(db, sale_id, current_user.id)

    return SaleResponse(
        id=sale.id,
        invoice_no=sale.invoice_no,
        user_id=sale.user_id,
        user_name=sale.user.name if sale.user else None,
        subtotal=sale.subtotal,
        discount=sale.discount,
        tax=sale.tax,
        total=sale.total,
        payment_method=sale.payment_method,
        status=sale.status,
        notes=sale.notes,
        customer_name=sale.customer_name,
        customer_phone=sale.customer_phone,
        customer_place=sale.customer_place,
        customer_email=sale.customer_email,
        items=[
            SaleItemResponse(
                id=item.id,
                product_id=item.product_id,
                product_name=item.product.name if item.product else None,
                product_barcode=item.product.barcode if item.product else None,
                quantity=item.quantity,
                unit_price=item.unit_price,
                discount=item.discount,
                tax_rate=item.tax_rate,
                tax=item.tax,
                subtotal=item.subtotal,
            )
            for item in sale.items
        ],
        created_at=sale.created_at,
    )

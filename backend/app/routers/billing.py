"""
Billing router — complete a sale.
"""
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.schemas.sale import BillRequest, SaleResponse, SaleItemResponse
from app.services.billing_service import complete_sale
from app.services.invoice_service import generate_invoice_html

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.post("/complete", response_model=SaleResponse)
def complete_bill(
    bill: BillRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Complete a sale — atomic transaction per TRD §13."""
    sale = complete_sale(db, bill, current_user.id)

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


@router.get("/invoice/{sale_id}", response_class=HTMLResponse)
def get_invoice(sale_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Get printable HTML invoice for a sale."""
    html = generate_invoice_html(db, sale_id)
    return HTMLResponse(content=html)

"""
Printer Router — Endpoints for direct raw hardware printing without browser dialog.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.sale import Sale
from app.services.invoice_service import get_store_settings
from app.services.printer_service import (
    get_available_printers,
    get_default_printer_name,
    send_raw_to_printer,
    build_tspl_label,
    build_escpos_receipt,
)

router = APIRouter(prefix="/printer", tags=["Printer"])


class DirectLabelRequest(BaseModel):
    product_name: str
    barcode: str
    price: Optional[float] = None
    store_name: Optional[str] = "MOIRA LUXE"
    copies: Optional[int] = 1
    width_mm: Optional[int] = 50
    height_mm: Optional[int] = 30
    printer_name: Optional[str] = None
    show_price: Optional[bool] = True
    show_header: Optional[bool] = True


@router.get("/list")
def list_printers():
    """List all locally installed Windows printers."""
    printers = get_available_printers()
    default_printer = get_default_printer_name()
    return {
        "printers": printers,
        "default": default_printer,
    }


@router.post("/print-label")
def direct_print_label(payload: DirectLabelRequest):
    """Send TSPL label command directly to DEV 632-L58P / Xprinter without browser popup."""
    try:
        raw_bytes = build_tspl_label(
            product_name=payload.product_name,
            barcode=payload.barcode,
            price=payload.price,
            store_name=payload.store_name or "MOIRA LUXE",
            copies=payload.copies or 1,
            width_mm=payload.width_mm or 50,
            height_mm=payload.height_mm or 30,
            show_price=payload.show_price if payload.show_price is not None else True,
            show_header=payload.show_header if payload.show_header is not None else True,
        )
        send_raw_to_printer(raw_bytes, payload.printer_name)
        return {"status": "ok", "message": f"Sent {payload.copies} label(s) directly to printer"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Direct print failed: {str(e)}")


class DirectReceiptPayload(BaseModel):
    invoice_no: Optional[str] = None
    items: Optional[List[dict]] = None
    subtotal: Optional[float] = None
    discount: Optional[float] = 0.0
    total: Optional[float] = None
    store_name: Optional[str] = None
    store_address: Optional[str] = None
    store_phone: Optional[str] = None
    currency_symbol: Optional[str] = "Rs."
    paper_width: Optional[str] = "80mm"


@router.post("/print-receipt/{sale_id}")
def direct_print_receipt(
    sale_id: int, 
    payload: Optional[DirectReceiptPayload] = None, 
    db: Session = Depends(get_db)
):
    """Send ESC/POS receipt commands directly to 58mm/80mm printer without browser popup."""
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    store = get_store_settings(db)
    
    if sale:
        invoice_no = sale.invoice_no
        items_data = [
            {
                "name": item.product.name if item.product else "Item",
                "quantity": item.quantity,
                "price": item.subtotal,
            }
            for item in sale.items
        ]
        subtotal = sale.subtotal
        discount = sale.discount
        total = sale.total
    elif payload and payload.invoice_no:
        invoice_no = payload.invoice_no
        items_data = payload.items or []
        subtotal = payload.subtotal or 0.0
        discount = payload.discount or 0.0
        total = payload.total or 0.0
    else:
        raise HTTPException(status_code=404, detail="Sale not found")

    try:
        raw_bytes = build_escpos_receipt(
            invoice_no=invoice_no,
            items=items_data,
            subtotal=subtotal,
            discount=discount,
            total=total,
            store_name=(payload and payload.store_name) or store.get("store_name", "MOIRA LUXE"),
            store_address=(payload and payload.store_address) or store.get("store_address", ""),
            store_phone=(payload and payload.store_phone) or store.get("store_phone", ""),
            currency_symbol=(payload and payload.currency_symbol) or store.get("currency_symbol", "Rs."),
            paper_width=(payload and payload.paper_width) or store.get("receipt_width", "80mm"),
        )
        send_raw_to_printer(raw_bytes)
        return {"status": "ok", "message": f"Printed receipt for {invoice_no}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Direct receipt print failed: {str(e)}")


@router.api_route("/test-receipt", methods=["GET", "POST"])
def direct_test_receipt(paper_width: Optional[str] = "80mm", db: Session = Depends(get_db)):
    """Print an instant test receipt directly to thermal printer with store details."""
    store = get_store_settings(db)
    chosen_width = paper_width or store.get("receipt_width", "80mm")
    
    test_items = [
        {"name": "Moira Silk Saree", "quantity": 1, "price": 1499.00},
        {"name": "Cotton Kurti (M)", "quantity": 2, "price": 998.00},
        {"name": "Printed Scarf", "quantity": 1, "price": 299.00},
    ]
    subtotal = 2796.00
    discount = 196.00
    total = 2600.00
    
    try:
        raw_bytes = build_escpos_receipt(
            invoice_no="TEST-0001",
            items=test_items,
            subtotal=subtotal,
            discount=discount,
            total=total,
            store_name=store.get("store_name", "MOIRA LUXE"),
            store_address=store.get("store_address", "Fashion Street, Retail Hub"),
            store_phone=store.get("store_phone", "9876543210"),
            currency_symbol=store.get("currency_symbol", "Rs."),
            paper_width=chosen_width,
        )
        send_raw_to_printer(raw_bytes)
        return {"status": "ok", "message": f"Printed test receipt ({chosen_width})"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Direct test receipt print failed: {str(e)}")


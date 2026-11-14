"""
Printer Router — Endpoints for direct raw hardware printing without browser dialog.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.sale import Sale
from app.services.invoice_service import get_store_settings, number_to_indian_words
from app.services.printer_service import (
    get_available_printers,
    get_default_printer_name,
    is_document_printer,
    send_raw_to_printer,
    build_tspl_label,
    print_receipt_direct,
)

router = APIRouter(prefix="/printer", tags=["Printer"])


class DirectLabelRequest(BaseModel):
    product_name: str
    barcode: str
    price: Optional[float] = None
    store_name: Optional[str] = "MOIRA LUXE"
    tag_details: Optional[str] = None
    copies: Optional[int] = 1
    width_mm: Optional[float] = 50
    height_mm: Optional[float] = 30
    label_type: Optional[str] = "normal"  # "normal" or "tagging"
    printer_name: Optional[str] = None
    show_price: Optional[bool] = True
    show_header: Optional[bool] = True
    show_qr: Optional[bool] = False
    enabled_columns: Optional[List[int]] = None


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
def direct_print_label(payload: DirectLabelRequest, db: Session = Depends(get_db)):
    """Send TSPL label command directly to DEV 632-L58P / Xprinter without browser popup."""
    try:
        store = get_store_settings(db)
        is_tagging = (payload.label_type == "tagging") or ((payload.width_mm or 50) <= 20 and (payload.height_mm or 30) >= 70)
        
        # Store / brand header (e.g. Moira Luxe)
        effective_store_name = payload.store_name or payload.tag_details or store.get("store_name", "Moira Luxe")

        raw_bytes = build_tspl_label(
            product_name=payload.product_name,
            barcode=payload.barcode,
            price=payload.price,
            store_name=effective_store_name,
            copies=payload.copies or 1,
            width_mm=payload.width_mm or (14.3 if is_tagging else 50),
            height_mm=payload.height_mm or (100.0 if is_tagging else 30),
            show_price=payload.show_price if payload.show_price is not None else True,
            show_header=payload.show_header if payload.show_header is not None else True,
            label_type="tagging" if is_tagging else "normal",
            show_qr=payload.show_qr or False,
            enabled_columns=payload.enabled_columns,
        )
        target_printer = payload.printer_name
        if not target_printer:
            all_printers = get_available_printers()
            label_printers = [p for p in all_printers if "label" in p.lower()]
            if label_printers:
                target_printer = label_printers[0]
        send_raw_to_printer(raw_bytes, target_printer)
        return {"status": "ok", "message": f"Sent {payload.copies} label(s) directly to printer"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Direct print failed: {str(e)}")


class DirectReceiptPayload(BaseModel):
    invoice_no: Optional[str] = None
    items: Optional[List[dict]] = None
    subtotal: Optional[float] = None
    discount: Optional[float] = 0.0
    total: Optional[float] = None
    payment_method: Optional[str] = "CASH"
    store_name: Optional[str] = None
    store_address: Optional[str] = None
    store_phone: Optional[str] = None
    currency_symbol: Optional[str] = "Rs."
    paper_width: Optional[str] = "A4"
    printer_name: Optional[str] = None


@router.post("/print-receipt/{sale_id}")
def direct_print_receipt(
    sale_id: int, 
    payload: Optional[DirectReceiptPayload] = None, 
    db: Session = Depends(get_db)
):
    """
    Intelligently routes print job:
    1. If target is an Epson EcoTank / Inkjet / Laser printer (or A4/A5 is selected):
       Routes to full-page/half-page document print format.
    2. If target is a thermal receipt printer:
       Sends native ESC/POS thermal command bytes.
    """
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    store = get_store_settings(db)
    payment_method = "CASH"
    
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
        payment_method = sale.payment_method or "CASH"
    elif payload and payload.invoice_no:
        invoice_no = payload.invoice_no
        items_data = payload.items or []
        subtotal = payload.subtotal or 0.0
        discount = payload.discount or 0.0
        total = payload.total or 0.0
        payment_method = payload.payment_method or "CASH"
    else:
        raise HTTPException(status_code=404, detail="Sale not found")

    target_printer = (payload and payload.printer_name) or get_default_printer_name()
    chosen_width = ((payload and payload.paper_width) or store.get("receipt_width", "A4")).upper()

    # Format creation date/time in Indian Standard Time (IST = UTC+5:30)
    created_at_str = None
    if sale and sale.created_at:
        try:
            from datetime import timedelta
            ist_time = sale.created_at + timedelta(hours=5, minutes=30)
            created_at_str = ist_time.strftime("%d-%m-%Y  %I:%M %p")
        except Exception:
            try:
                created_at_str = sale.created_at.strftime("%d-%m-%Y  %I:%M %p")
            except Exception:
                pass
    if not created_at_str:
        from datetime import datetime, timezone, timedelta
        IST = timezone(timedelta(hours=5, minutes=30))
        created_at_str = datetime.now(IST).strftime("%d-%m-%Y  %I:%M %p")

    cust_name = (sale and sale.customer_name) or "Walk-in Customer"
    cust_phone = (sale and sale.customer_phone) or "-"
    cust_place = (sale and sale.customer_place) or "Thuckalay"

    # Detect if printer is an Epson L6460 / Inkjet / Laser or if A4/A5 is configured
    is_doc = is_document_printer(target_printer) or ("A4" in chosen_width) or ("A5" in chosen_width)
    if is_doc:
        doc_format = "A5" if "A5" in chosen_width else "A4"
        success = False
        try:
            success = print_receipt_direct(
                invoice_no=invoice_no,
                items=items_data,
                subtotal=subtotal,
                discount=discount,
                total=total,
                store_name=(payload and payload.store_name) or store.get("store_name", "MOIRA LUXE"),
                store_address=(payload and payload.store_address) or store.get("store_address", "Thuckalay"),
                store_phone=(payload and payload.store_phone) or store.get("store_phone", "8438353504"),
                currency_symbol=(payload and payload.currency_symbol) or store.get("currency_symbol", "Rs."),
                paper_width=doc_format,
                printer_name=target_printer,
                customer_name=cust_name,
                customer_phone=cust_phone,
                created_at=created_at_str,
                payment_method=payment_method,
            )
        except Exception as e:
            print(f"Direct spool to {target_printer} error: {e}")

        return {
            "status": "ok" if success else "error",
            "printed": success,
            "printer_type": "document",
            "format": doc_format,
            "target_printer": target_printer,
            "invoice_url": f"/api/billing/invoice/{sale_id}?format={doc_format}",
            "message": f"Tax Invoice dispatched to {target_printer} ({doc_format})",
        }

    try:
        print_receipt_direct(
            invoice_no=invoice_no,
            items=items_data,
            subtotal=subtotal,
            discount=discount,
            total=total,
            store_name=(payload and payload.store_name) or store.get("store_name", "MOIRA LUXE"),
            store_address=(payload and payload.store_address) or store.get("store_address", "Thuckalay"),
            store_phone=(payload and payload.store_phone) or store.get("store_phone", "8438353504"),
            currency_symbol=(payload and payload.currency_symbol) or store.get("currency_symbol", "Rs."),
            paper_width=(payload and payload.paper_width) or store.get("receipt_width", "58mm"),
            created_at=created_at_str,
            payment_method=payment_method,
            printer_name=target_printer,
        )
        return {"status": "ok", "printer_type": "thermal", "message": f"Printed receipt for {invoice_no}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Direct receipt print failed: {str(e)}")


@router.get("/sample-invoice", response_class=HTMLResponse)
def get_sample_invoice(format: Optional[str] = Query("A4", description="Format: A4, A5, 58mm, 80mm"), db: Session = Depends(get_db)):
    """Render a live sample invoice formatted specifically for Epson L6460 (A4/A5) or thermal printers."""
    store = get_store_settings(db)
    chosen_fmt = (format or "A4").upper()
    is_a5 = "A5" in chosen_fmt
    currency = store.get("currency_symbol", "Rs.")
    
    sample_items = [
        {"name": "22K Gold Plated Choker Necklace", "code": "JW-CH-01", "qty": 1, "rate": 3499.00, "disc": 200.00, "amount": 3299.00},
        {"name": "Kundan Pearl Drop Earrings (Pair)", "code": "JW-ER-08", "qty": 2, "rate": 1250.00, "disc": 100.00, "amount": 2400.00},
        {"name": "Diamond Cut Silver Plated Bangle", "code": "JW-BG-14", "qty": 1, "rate": 1899.00, "disc": 50.00, "amount": 1849.00},
    ]
    subtotal = sum(i["qty"] * i["rate"] for i in sample_items)
    discount = sum(i["disc"] for i in sample_items)
    tax = 226.44  # 3% GST on jewellery
    total = (subtotal - discount) + tax
    amount_in_words = number_to_indian_words(total)

    from datetime import datetime, timezone, timedelta
    IST = timezone(timedelta(hours=5, minutes=30))
    now_str = datetime.now(IST).strftime("%d-%m-%Y  %I:%M %p")

    # If thermal format requested
    if "58" in chosen_fmt or "80" in chosen_fmt:
        return HTMLResponse(content=f"""
        <!DOCTYPE html><html><body style="font-family:monospace; padding:10px; text-align:center;">
        <h3>{store['store_name']}</h3>
        <p>Sample Thermal Receipt ({chosen_fmt})</p>
        <hr>
        <p>Total: {currency} {total:,.2f}</p>
        </body></html>
        """)

    # High-quality A4/A5 Document Format for Epson L6460
    page_size_css = "A5 landscape" if is_a5 else "A4 portrait"
    page_margin_css = "8mm" if is_a5 else "12mm"
    base_font_size = "12px" if is_a5 else "13.5px"

    rows_html = ""
    for idx, item in enumerate(sample_items, 1):
        rows_html += f"""
        <tr>
            <td style="text-align:center; padding:7px 8px; border:1px solid #cbd5e1;">{idx}</td>
            <td style="padding:7px 10px; border:1px solid #cbd5e1;">
                <div style="font-weight:600; color:#0f172a;">{item['name']}</div>
                <div style="font-size:11px; color:#64748b;">Code: {item['code']}</div>
            </td>
            <td style="text-align:center; padding:7px 8px; border:1px solid #cbd5e1; font-weight:600;">{item['qty']}</td>
            <td style="text-align:right; padding:7px 8px; border:1px solid #cbd5e1;">{currency} {item['rate']:,.2f}</td>
            <td style="text-align:right; padding:7px 8px; border:1px solid #cbd5e1; color:#dc2626;">-{currency} {item['disc']:,.2f}</td>
            <td style="text-align:right; padding:7px 8px; border:1px solid #cbd5e1; font-weight:700;">{currency} {item['amount']:,.2f}</td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Sample Invoice - Epson L6460 ({chosen_fmt})</title>
        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/JsBarcode.all.min.js"></script>
        <style>
            * {{ margin:0; padding:0; box-sizing:border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
            body {{
                background:#f1f5f9;
                color:#0f172a;
                font-size:{base_font_size};
                padding: 24px;
            }}
            .invoice-container {{
                max-width: { '750px' if is_a5 else '820px' };
                margin: 0 auto;
                background: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: { '18px 24px' if is_a5 else '28px 36px' };
                box-shadow: 0 10px 15px -3px rgba(0,0,0,0.07);
            }}
            .header-table {{ width:100%; border-collapse:collapse; margin-bottom:14px; }}
            .store-title {{ font-size:{ '22px' if is_a5 else '28px' }; font-weight:800; letter-spacing:1px; color:#0f172a; text-transform:uppercase; }}
            .store-sub {{ font-size:11.5px; color:#475569; margin-top:4px; line-height:1.45; }}
            .badge-invoice {{
                display:inline-block;
                background:#0f172a;
                color:#ffffff;
                font-weight:700;
                font-size:12px;
                padding:5px 14px;
                border-radius:4px;
                text-transform:uppercase;
                letter-spacing:1px;
            }}
            .info-grid {{
                width: 100%;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                border-collapse: collapse;
                margin-bottom: 14px;
                background: #f8fafc;
            }}
            .info-grid td {{ padding: 10px 14px; vertical-align: top; font-size: 12px; }}
            .info-grid td:first-child {{ border-right: 1px solid #cbd5e1; width: 50%; }}
            .info-label {{ font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 700; margin-bottom: 3px; }}
            .info-val {{ font-weight: 600; color: #0f172a; }}
            
            .items-table {{ width:100%; border-collapse:collapse; margin-bottom:14px; }}
            .items-table th {{
                background:#f8fafc;
                color:#334155;
                font-size:11px;
                font-weight:700;
                text-transform:uppercase;
                letter-spacing:0.5px;
                padding:9px 8px;
                border:1px solid #cbd5e1;
            }}
            
            .summary-table {{ width:100%; border-collapse:collapse; margin-top:6px; }}
            .summary-table td {{ padding:4px 8px; font-size:12.5px; }}
            .grand-total-row td {{
                font-size: 15px;
                font-weight: 800;
                color: #0f172a;
                border-top: 2px solid #0f172a;
                border-bottom: 2px solid #0f172a;
                padding: 8px 8px;
            }}
            
            .footer-box {{
                margin-top: 18px;
                padding-top: 14px;
                border-top: 1px dashed #cbd5e1;
                display: flex;
                justify-content: space-between;
                align-items: flex-end;
            }}
            .terms {{ font-size: 10.5px; color: #64748b; max-width: 60%; line-height: 1.45; }}
            .sign-box {{ text-align: center; min-width: 180px; }}
            .sign-line {{ border-bottom: 1px solid #0f172a; width: 140px; margin: 0 auto 6px auto; height: 35px; }}
            .sign-label {{ font-size: 11px; font-weight: 700; color: #0f172a; text-transform: uppercase; }}

            @media print {{
                @page {{
                    size: {page_size_css};
                    margin: {page_margin_css};
                }}
                body {{
                    background: #ffffff !important;
                    padding: 0 !important;
                    margin: 0 !important;
                    -webkit-print-color-adjust: exact;
                    print-color-adjust: exact;
                }}
                .invoice-container {{
                    border: none !important;
                    box-shadow: none !important;
                    padding: 0 !important;
                    width: 100% !important;
                    max-width: 100% !important;
                }}
                .no-print {{ display: none !important; }}
            }}
        </style>
    </head>
    <body>
        <div class="no-print" style="max-width:{'750px' if is_a5 else '820px'}; margin:0 auto 16px auto; display:flex; justify-content:space-between; align-items:center; background:#ffffff; padding:12px 18px; border-radius:8px; border:1px solid #cbd5e1;">
            <div style="display:flex; align-items:center; gap:12px;">
                <button onclick="window.print()" style="background:#0284c7; color:#fff; border:none; padding:10px 22px; border-radius:6px; cursor:pointer; font-weight:700; font-size:13px; display:flex; align-items:center; gap:8px;">
                    🖨️ Print Sample to Epson L6460
                </button>
                <a href="/api/printer/sample-invoice?format={'A5' if not is_a5 else 'A4'}" style="color:#0284c7; font-size:12px; font-weight:600; text-decoration:none;">
                    Switch to {'A5 (Half Sheet)' if not is_a5 else 'A4 (Full Page)'}
                </a>
            </div>
            <span style="font-size:12px; color:#64748b;">Target Printer: <strong>Epson EcoTank L6460</strong> ({'A5 Half Sheet' if is_a5 else 'A4 Full Page'})</span>
        </div>

        <div class="invoice-container">
            <!-- Header -->
            <table class="header-table">
                <tr>
                    <td style="vertical-align:top;">
                        <div class="store-title">{store['store_name']}</div>
                        <div class="store-sub">
                            {store['store_address']}<br>
                            Phone: <strong>{store['store_phone']}</strong> | Email: {store['store_email']}<br>
                            {f"<strong>GSTIN:</strong> {store['store_gst']}" if store['store_gst'] else ""}
                        </div>
                    </td>
                    <td style="text-align:right; vertical-align:top;">
                        <div class="badge-invoice">TAX INVOICE</div>
                        <div style="margin-top:8px;">
                            <svg id="barcode"></svg>
                        </div>
                    </td>
                </tr>
            </table>

            <!-- Info Grid -->
            <table class="info-grid">
                <tr>
                    <td>
                        <div class="info-label">Invoice Details</div>
                        <div><strong>Invoice No:</strong> ML-SAMPLE-2026</div>
                        <div><strong>Date & Time:</strong> {now_str}</div>
                        <div><strong>Payment Mode:</strong> <span style="text-transform:uppercase; color:#0f172a; font-weight:700;">UPI / GPAY</span></div>
                        <div><strong>Cashier:</strong> Ajay (Manager)</div>
                    </td>
                    <td>
                        <div class="info-label">Customer Details (Billed To)</div>
                        <div class="info-val">Priyadharshini M</div>
                        <div>Phone: +91 98765 43210</div>
                        <div>Address: Thuckalay, Kanyakumari Dist</div>
                    </td>
                </tr>
            </table>

            <!-- Items Table -->
            <table class="items-table">
                <thead>
                    <tr>
                        <th style="width:5%;">#</th>
                        <th style="width:45%; text-align:left;">Item Description</th>
                        <th style="width:10%; text-align:center;">Qty</th>
                        <th style="width:14%; text-align:right;">Rate</th>
                        <th style="width:11%; text-align:right;">Disc</th>
                        <th style="width:15%; text-align:right;">Amount</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>

            <!-- Totals Section -->
            <table style="width:100%; border-collapse:collapse;">
                <tr>
                    <td style="vertical-align:top; width:55%; padding-right:16px;">
                        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:10px 14px; margin-top:4px;">
                            <div style="font-size:11px; text-transform:uppercase; color:#64748b; font-weight:700;">Amount in Words:</div>
                            <div style="font-weight:700; color:#0f172a; font-size:12px; margin-top:2px;">{amount_in_words}</div>
                            <div style="margin-top:6px; font-size:11.5px; color:#475569;">Total Items: <strong>3</strong> | Total Qty: <strong>4</strong></div>
                        </div>
                    </td>
                    <td style="vertical-align:top; width:45%;">
                        <table class="summary-table">
                            <tr>
                                <td style="color:#64748b;">Subtotal:</td>
                                <td style="text-align:right; font-weight:600;">{currency} {subtotal:,.2f}</td>
                            </tr>
                            <tr>
                                <td style="color:#dc2626;">Total Discount:</td>
                                <td style="text-align:right; font-weight:600; color:#dc2626;">-{currency} {discount:,.2f}</td>
                            </tr>
                            <tr>
                                <td style="color:#64748b;">GST (3%):</td>
                                <td style="text-align:right; font-weight:600;">+{currency} {tax:,.2f}</td>
                            </tr>
                            <tr class="grand-total-row">
                                <td>TOTAL PAYABLE:</td>
                                <td style="text-align:right;">{currency} {total:,.2f}</td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>

            <!-- Footer -->
            <div class="footer-box">
                <div class="terms" style="max-width: 100%;">
                    <strong>Terms & Conditions:</strong><br>
                    1. Goods once sold can be exchanged within 7 days with original tax invoice.<br>
                    2. No cash refund on sold jewellery items.<br>
                    3. Thank you for shopping with <strong>{store['store_name']}</strong>!
                </div>
            </div>
        </div>

        <script>
            window.onload = function() {{
                if (typeof JsBarcode !== 'undefined') {{
                    JsBarcode("#barcode", "ML-SAMPLE-2026", {{
                        format: "CODE128",
                        width: 1.15,
                        height: 28,
                        fontSize: 10,
                        margin: 0,
                        displayValue: true
                    }});
                }}
            }};
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.api_route("/test-invoice", methods=["GET", "POST"])
def direct_test_invoice(format: Optional[str] = "A4", printer_name: Optional[str] = None, db: Session = Depends(get_db)):
    """Directly print a sample Tax Invoice to Epson EcoTank L6460 or default document printer."""
    store = get_store_settings(db)
    target = printer_name or get_default_printer_name() or "L6460 Series(Network)"
    chosen_fmt = (format or "A4").upper()
    
    test_items = [
        {"name": "22K Gold Plated Choker Necklace", "code": "JW-CH-01", "quantity": 1, "price": 3499.00, "discount": 200.00, "amount": 3299.00},
        {"name": "Kundan Pearl Drop Earrings (Pair)", "code": "JW-ER-08", "quantity": 2, "price": 1250.00, "discount": 100.00, "amount": 2400.00},
        {"name": "Diamond Cut Silver Plated Bangle", "code": "JW-BG-14", "quantity": 1, "price": 1899.00, "discount": 50.00, "amount": 1849.00},
    ]
    subtotal = 6648.00
    discount = 350.00
    total = 6487.00
    
    from datetime import datetime, timezone, timedelta
    IST = timezone(timedelta(hours=5, minutes=30))
    now_str = datetime.now(IST).strftime("%d-%m-%Y  %I:%M %p")

    try:
        success = print_receipt_direct(
            invoice_no="ML-SAMPLE-2026",
            items=test_items,
            subtotal=subtotal,
            discount=discount,
            total=total,
            store_name=store.get("store_name", "MOIRA LUXE"),
            store_address=store.get("store_address", "Main Road, Thuckalay"),
            store_phone=store.get("store_phone", "8438353504"),
            currency_symbol=store.get("currency_symbol", "Rs."),
            paper_width=chosen_fmt,
            printer_name=target,
            customer_name="Priyadharshini M",
            customer_phone="+91 98765 43210",
            created_at=now_str,
            payment_method="CASH / UPI",
        )
        if success:
            return {"status": "ok", "message": f"Sample {chosen_fmt} Tax Invoice printed to {target}"}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to print sample invoice to {target}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Print error: {str(e)}")


@router.api_route("/test-receipt", methods=["GET", "POST"])
def direct_test_receipt(paper_width: Optional[str] = "58mm", db: Session = Depends(get_db)):
    """Print an instant test receipt directly to thermal printer with store details."""
    store = get_store_settings(db)
    chosen_width = paper_width or store.get("receipt_width", "58mm")
    
    test_items = [
        {"name": "Moira Silk Saree", "quantity": 1, "price": 1499.00},
        {"name": "Cotton Kurti (M)", "quantity": 2, "price": 998.00},
        {"name": "Printed Scarf", "quantity": 1, "price": 299.00},
    ]
    subtotal = 2796.00
    discount = 196.00
    total = 2600.00
    
    try:
        print_receipt_direct(
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
        return {"status": "ok", "message": f"Printed test receipt ({chosen_width})"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Direct test receipt print failed: {str(e)}")


@router.api_route("/test-label", methods=["GET", "POST"])
def direct_test_label(label_size: Optional[str] = "14x100mm", db: Session = Depends(get_db)):
    """Print an instant test sample label directly to the thermal label printer."""
    store = get_store_settings(db)
    size_str = str(label_size or "").lower()
    is_jewellery = "14" in size_str or "100" in size_str
    width = 14.3 if is_jewellery else (50.0 if "50" in size_str else 40.0)
    height = 100.0 if is_jewellery else (25.0 if "25" in size_str else 30.0)

    try:
        raw_bytes = build_tspl_label(
            product_name="24K GOLD RING" if is_jewellery else "Moira Luxury Item",
            barcode="94685000" if is_jewellery else "ML-10023",
            price=26900.0 if is_jewellery else 1299.0,
            store_name="wt. 2.5gm" if is_jewellery else store.get("store_name", "MOIRA LUXE"),
            copies=1,
            width_mm=width,
            height_mm=height,
            show_price=True,
            show_header=True,
        )
        all_printers = get_available_printers()
        target_printer = None
        label_printers = [p for p in all_printers if "label" in p.lower()]
        if label_printers:
            target_printer = label_printers[0]
        send_raw_to_printer(raw_bytes, target_printer)
        return {"status": "ok", "message": f"Sent sample {label_size} label directly to printer"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Direct test label print failed: {str(e)}")



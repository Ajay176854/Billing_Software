"""
Invoice Service — generate printable HTML invoice/receipt.
"""
from sqlalchemy.orm import Session, joinedload
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.setting import Setting
from fastapi import HTTPException


def get_store_settings(db: Session) -> dict:
    """Load store profile settings from the database."""
    settings = db.query(Setting).all()
    settings_dict = {s.key: s.value for s in settings}
    return {
        "store_name": settings_dict.get("store_name", "MOIRA LUXE"),
        "store_address": settings_dict.get("store_address", ""),
        "store_phone": settings_dict.get("store_phone", ""),
        "store_email": settings_dict.get("store_email", ""),
        "store_gst": settings_dict.get("store_gst", ""),
        "currency_symbol": settings_dict.get("currency_symbol", "Rs."),
        "receipt_width": settings_dict.get("receipt_width", "80mm"),
        "auto_print": settings_dict.get("auto_print", "true"),
    }


def generate_invoice_html(db: Session, sale_id: int) -> str:
    """Generate a printable HTML invoice for a sale."""
    sale = db.query(Sale).options(joinedload(Sale.items).joinedload(SaleItem.product)).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    store = get_store_settings(db)
    currency = store["currency_symbol"]
    receipt_width = store.get("receipt_width", "58mm")
    is_58mm = "58" in str(receipt_width)

    max_width_px = "216px" if is_58mm else "290px"
    font_size = "10.5px" if is_58mm else "12px"
    store_font_size = "17px" if is_58mm else "20px"
    barcode_width = 1.0 if is_58mm else 1.3
    barcode_height = 28 if is_58mm else 36

    items_html = ""
    for idx, item in enumerate(sale.items, 1):
        product_name = item.product.name if item.product else "Unknown"
        items_html += f"""
        <tr>
            <td colspan="3" class="item-name">{product_name}</td>
        </tr>
        <tr>
            <td class="item-details">{item.quantity} x {currency}{item.unit_price:,.2f}</td>
            <td class="item-details" style="text-align:center;">{f"-{currency}{item.discount:,.2f}" if item.discount else ""}</td>
            <td class="item-total">{currency}{item.subtotal:,.2f}</td>
        </tr>
        """

    created = sale.created_at.strftime("%d-%m-%Y %I:%M %p") if sale.created_at else ""
    cashier = sale.user.name if sale.user else ""

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Receipt {sale.invoice_no}</title>
        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/JsBarcode.all.min.js"></script>
        <style>
            * {{ margin:0; padding:0; box-sizing:border-box; font-family:'Courier New', Courier, monospace; }}
            html, body {{ 
                color:#000; 
                background:#fff;
                height:auto !important;
                min-height:auto !important;
            }}
            body {{ 
                max-width:{max_width_px}; 
                margin:0 auto; 
                padding:6px 6px; 
                font-size:{font_size}; 
            }}
            .receipt-content {{
                width: 100%;
                page-break-inside: avoid !important;
                break-inside: avoid !important;
            }}
            .header {{ text-align:center; margin-bottom:10px; padding-bottom:8px; border-bottom:1px dashed #000; }}
            .store-name {{ text-align:center; font-size:{store_font_size}; font-weight:800; letter-spacing:0.5px; text-transform:uppercase; word-break:break-word; }}
            .store-info {{ text-align:center; font-size:10.5px; margin-top:4px; line-height:1.3; }}
            .invoice-meta {{ margin-bottom:10px; font-size:10.5px; padding-bottom:8px; line-height:1.4; border-bottom:1px dashed #000; }}
            .invoice-meta div {{ margin-bottom:3px; }}
            table {{ width:100%; border-collapse:collapse; margin-bottom:10px; font-size:{font_size}; table-layout:fixed; page-break-inside: avoid !important; }}
            th {{ border-bottom:1px dashed #000; padding:4px 2px; text-align:left; font-weight:700; font-size:10px; text-transform:uppercase; }}
            th.th-item {{ width:46%; }}
            th.th-disc {{ width:16%; text-align:center; }}
            th.th-amount {{ width:38%; text-align:right; }}
            td {{ padding:2.5px 1px; }}
            .item-name {{ font-weight:700; padding-top:4px; word-break:break-word; }}
            .item-details {{ font-size:10px; color:#111; }}
            .item-total {{ text-align:right; font-weight:700; white-space:nowrap; }}
            .totals {{ width:100%; font-size:{font_size}; border-top:1px dashed #000; padding-top:8px; margin-bottom:10px; }}
            .totals tr td {{ padding:2.5px 1px; }}
            .totals tr td:last-child {{ white-space:nowrap; }}
            .totals .grand-total {{ font-size:14px; font-weight:800; border-top:1px dashed #000; border-bottom:1px dashed #000; padding:6px 1px; }}
            .footer {{ text-align:center; margin-top:12px; padding-top:8px; font-size:10px; line-height:1.35; page-break-inside: avoid !important; }}
            .barcode-container {{ text-align:center; margin-top:6px; display:flex; justify-content:center; page-break-inside: avoid !important; }}
            .barcode-container svg {{ shape-rendering: crispEdges; max-width: 90%; height: auto; }}
            @media print {{
                @page {{ 
                    margin: 0 !important; 
                    size: {receipt_width} auto; 
                }}
                html, body {{ 
                    margin: 0 !important; 
                    padding: 1mm 2mm !important; 
                    width: 100% !important; 
                    max-width: 100% !important; 
                    -webkit-print-color-adjust: exact; 
                    print-color-adjust: exact; 
                }}
                .receipt-content {{
                    page-break-inside: avoid !important;
                    break-inside: avoid !important;
                }}
                .no-print {{ display:none !important; }}
            }}
        </style>
    </head>
    <body>
        <div class="no-print" style="margin-bottom:20px; text-align:center;">
            <button onclick="window.print()" style="background:#0f172a; color:white; border:none; padding:10px 20px; border-radius:4px; cursor:pointer; font-weight:600; font-family:sans-serif;">🖨️ Print Receipt</button>
        </div>
        
        <div class="receipt-content">
            <div class="header">
                <div class="store-name">{store['store_name']}</div>
                <div class="store-info">
                    {f"{store['store_address']} - {store['store_phone']}".strip(" -") if (store['store_address'] or store['store_phone']) else ""}
                    {f"<br>{store['store_email']}" if store['store_email'] else ""}
                    {f"<br>GST: {store['store_gst']}" if store['store_gst'] else ""}
                </div>
            </div>

            <div class="invoice-meta">
                <div><strong>Bill No:</strong> {sale.invoice_no}</div>
                <div><strong>Date:</strong> {created}</div>
                <div><strong>Cashier:</strong> {cashier}</div>
                <div><strong>Payment:</strong> {sale.payment_method.upper()}</div>
            </div>

            {"" if not any([sale.customer_name, sale.customer_phone, sale.customer_place, sale.customer_email]) else f'''
            <div style="margin-bottom:15px;font-size:11px; border-bottom:1px dashed #000; padding-bottom:10px;">
                <div style="font-weight:700;margin-bottom:4px;text-transform:uppercase;">Customer</div>
                {f'<div>{sale.customer_name}</div>' if sale.customer_name else ''}
                {f'<div>{sale.customer_phone}</div>' if sale.customer_phone else ''}
            </div>
            '''}

            <table>
                <thead>
                    <tr>
                        <th class="th-item">Item</th>
                        <th class="th-disc">Disc</th>
                        <th class="th-amount">Amount</th>
                    </tr>
                </thead>
                <tbody>
                    {items_html}
                </tbody>
            </table>

            <table class="totals">
                <tr><td>Subtotal</td><td style="text-align:right;">{currency} {sale.subtotal:,.2f}</td></tr>
                {f"<tr><td>Discount</td><td style='text-align:right;'>-{currency} {sale.discount:,.2f}</td></tr>" if sale.discount and sale.discount > 0 else ""}
                {f"<tr><td>Tax</td><td style='text-align:right;'>+{currency} {sale.tax:,.2f}</td></tr>" if sale.tax and sale.tax > 0 else ""}
                <tr class="grand-total"><td>Total</td><td style="text-align:right;">{currency} {sale.total:,.2f}</td></tr>
            </table>

            <div class="barcode-container">
                <svg id="barcode"></svg>
            </div>

            <div class="footer">
                <strong>Thank you for shopping!</strong><br>
                {f"GSTIN: {store['store_gst']}" if store['store_gst'] else ""}
            </div>
        </div>

        <script>
            window.onload = function() {{
                if (typeof JsBarcode !== 'undefined') {{
                    JsBarcode("#barcode", "{sale.invoice_no}", {{
                        format: "CODE128",
                        width: {barcode_width},
                        height: {barcode_height},
                        fontSize: 11,
                        margin: 0,
                        displayValue: true,
                        fontOptions: "bold"
                    }});
                }}
            }};
        </script>
    </body>
    </html>
    """
    return html

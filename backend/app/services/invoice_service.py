"""
Invoice Service — generate printable HTML invoice/receipt.
"""
from sqlalchemy.orm import Session
from app.models.sale import Sale
from app.models.setting import Setting
from fastapi import HTTPException


def get_store_settings(db: Session) -> dict:
    """Load store profile settings from the database."""
    settings = db.query(Setting).all()
    settings_dict = {s.key: s.value for s in settings}
    return {
        "store_name": settings_dict.get("store_name", "My Retail Store"),
        "store_address": settings_dict.get("store_address", ""),
        "store_phone": settings_dict.get("store_phone", ""),
        "store_email": settings_dict.get("store_email", ""),
        "store_gst": settings_dict.get("store_gst", ""),
        "currency_symbol": settings_dict.get("currency_symbol", "₹"),
    }


def generate_invoice_html(db: Session, sale_id: int) -> str:
    """Generate a printable HTML invoice for a sale."""
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    store = get_store_settings(db)
    currency = store["currency_symbol"]

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
            body {{ color:#000; max-width:320px; margin:0 auto; padding:15px; font-size:12px; background:#fff; }}
            .header {{ text-align:center; margin-bottom:15px; padding-bottom:10px; border-bottom:1px dashed #000; }}
            .store-name {{ font-size:18px; font-weight:700; text-transform:uppercase; }}
            .store-info {{ font-size:11px; margin-top:4px; }}
            .invoice-meta {{ margin-bottom:15px; font-size:11px; padding-bottom:10px; border-bottom:1px dashed #000; }}
            .invoice-meta div {{ margin-bottom:4px; }}
            table {{ width:100%; border-collapse:collapse; margin-bottom:15px; font-size:12px; }}
            th {{ border-bottom:1px dashed #000; padding:4px 0; text-align:left; font-weight:600; font-size:11px; text-transform:uppercase; }}
            td {{ padding:2px 0; }}
            .item-name {{ font-weight:700; padding-top:6px; }}
            .item-details {{ font-size:11px; color:#333; }}
            .item-total {{ text-align:right; font-weight:700; }}
            .totals {{ width:100%; font-size:12px; border-top:1px dashed #000; padding-top:10px; }}
            .totals tr td {{ padding:4px 0; }}
            .totals .grand-total {{ font-size:16px; font-weight:700; border-top:1px dashed #000; border-bottom:1px dashed #000; padding:8px 0; }}
            .footer {{ text-align:center; margin-top:15px; padding-top:10px; font-size:11px; }}
            .barcode-container {{ text-align:center; margin-top:20px; display:flex; justify-content:center; }}
            .barcode-container svg {{ shape-rendering: crispEdges; }}
            @media print {{
                @page {{ margin: 0; size: 80mm auto; }}
                body {{ padding: 0; max-width: 100%; width: 100%; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
                .no-print {{ display:none; }}
            }}
        </style>
    </head>
    <body>
        <div class="no-print" style="margin-bottom:20px; text-align:center;">
            <button onclick="window.print()" style="background:#0f172a; color:white; border:none; padding:10px 20px; border-radius:4px; cursor:pointer; font-weight:600; font-family:sans-serif;">🖨️ Print Receipt</button>
        </div>
        
        <div class="header">
            <div class="store-name">{store['store_name']}</div>
            <div class="store-info">
                {store['store_address']}<br>
                {f"Ph: {store['store_phone']}" if store['store_phone'] else ""}
                {f" | {store['store_email']}" if store['store_email'] else ""}
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
                    <th>Item</th>
                    <th style="text-align:center;">Disc</th>
                    <th style="text-align:right;">Amount</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
        </table>

        <table class="totals">
            <tr><td>Subtotal</td><td style="text-align:right;">{currency}{sale.subtotal:,.2f}</td></tr>
            <tr><td>Discount</td><td style="text-align:right;">-{currency}{sale.discount:,.2f}</td></tr>
            <tr><td>Tax</td><td style="text-align:right;">+{currency}{sale.tax:,.2f}</td></tr>
            <tr class="grand-total"><td>Total</td><td style="text-align:right;">{currency}{sale.total:,.2f}</td></tr>
        </table>

        <div class="barcode-container">
            <svg id="barcode"></svg>
        </div>

        <div class="footer">
            <strong>Thank you for shopping!</strong><br>
            {f"GSTIN: {store['store_gst']}" if store['store_gst'] else ""}
        </div>

        <script>
            window.onload = function() {{
                if (typeof JsBarcode !== 'undefined') {{
                    JsBarcode("#barcode", "{sale.invoice_no}", {{
                        format: "CODE128",
                        width: 1.5,
                        height: 40,
                        fontSize: 12,
                        margin: 0,
                        displayValue: true,
                        fontOptions: "bold"
                    }});
                }}
                setTimeout(function() {{
                    window.print();
                }}, 800);
            }};
        </script>
    </body>
    </html>
    """
    return html

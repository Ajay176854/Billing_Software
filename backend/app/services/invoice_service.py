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
            <td style="padding:8px;border-bottom:1px solid #e2e8f0;">{idx}</td>
            <td style="padding:8px;border-bottom:1px solid #e2e8f0;">{product_name}</td>
            <td style="padding:8px;border-bottom:1px solid #e2e8f0;text-align:center;">{item.quantity}</td>
            <td style="padding:8px;border-bottom:1px solid #e2e8f0;text-align:right;">{currency}{item.unit_price:,.2f}</td>
            <td style="padding:8px;border-bottom:1px solid #e2e8f0;text-align:right;">{currency}{item.discount:,.2f}</td>
            <td style="padding:8px;border-bottom:1px solid #e2e8f0;text-align:right;">{item.tax_rate}%</td>
            <td style="padding:8px;border-bottom:1px solid #e2e8f0;text-align:right;font-weight:600;">{currency}{item.subtotal:,.2f}</td>
        </tr>
        """

    created = sale.created_at.strftime("%d-%m-%Y %I:%M %p") if sale.created_at else ""
    cashier = sale.user.name if sale.user else ""

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Invoice {sale.invoice_no}</title>
        <style>
            * {{ margin:0; padding:0; box-sizing:border-box; }}
            body {{ font-family:'Segoe UI',system-ui,sans-serif; color:#1e293b; max-width:800px; margin:0 auto; padding:20px; }}
            .header {{ text-align:center; margin-bottom:24px; border-bottom:2px solid #0f172a; padding-bottom:16px; }}
            .store-name {{ font-size:24px; font-weight:700; color:#0f172a; }}
            .store-info {{ font-size:12px; color:#64748b; margin-top:4px; }}
            .invoice-meta {{ display:flex; justify-content:space-between; margin-bottom:20px; font-size:13px; }}
            .invoice-meta div {{ flex:1; }}
            .invoice-no {{ font-size:16px; font-weight:700; color:#0f172a; }}
            table {{ width:100%; border-collapse:collapse; margin-bottom:20px; font-size:13px; }}
            th {{ background:#0f172a; color:white; padding:10px 8px; text-align:left; font-weight:600; }}
            th:nth-child(3),th:nth-child(4),th:nth-child(5),th:nth-child(6),th:nth-child(7) {{ text-align:right; }}
            .totals {{ width:300px; margin-left:auto; font-size:14px; }}
            .totals tr td {{ padding:6px 8px; }}
            .totals .grand-total {{ font-size:18px; font-weight:700; border-top:2px solid #0f172a; color:#0f172a; }}
            .footer {{ text-align:center; margin-top:30px; padding-top:16px; border-top:1px solid #e2e8f0; font-size:12px; color:#94a3b8; }}
            .payment-badge {{ display:inline-block; background:#059669; color:white; padding:4px 12px; border-radius:12px; font-size:12px; font-weight:600; text-transform:uppercase; }}
            @media print {{
                body {{ padding:10px; }}
                .no-print {{ display:none; }}
            }}
        </style>
    </head>
    <body>
        <div class="no-print" style="margin-bottom:20px; text-align:right;">
            <button onclick="window.print()" style="background:#0f172a; color:white; border:none; padding:8px 16px; border-radius:6px; cursor:pointer; font-weight:600;">🖨️ Print Invoice</button>
        </div>
        <div class="header">
            <div class="store-name">{store['store_name']}</div>
            <div class="store-info">
                {store['store_address']}<br>
                {f"Phone: {store['store_phone']}" if store['store_phone'] else ""}
                {f" | Email: {store['store_email']}" if store['store_email'] else ""}
                {f"<br>GSTIN: {store['store_gst']}" if store['store_gst'] else ""}
            </div>
        </div>

        <div class="invoice-meta">
            <div>
                <div class="invoice-no">Invoice: {sale.invoice_no}</div>
                <div>Date: {created}</div>
            </div>
            <div style="text-align:right;">
                <div>Cashier: {cashier}</div>
                <div>Payment: <span class="payment-badge">{sale.payment_method}</span></div>
            </div>
        </div>

        {"" if not any([sale.customer_name, sale.customer_phone, sale.customer_place, sale.customer_email]) else f'''
        <div style="margin-bottom:20px;padding:12px 16px;border:1px solid #e2e8f0;border-radius:8px;font-size:13px;">
            <div style="font-weight:700;color:#0f172a;margin-bottom:6px;font-size:14px;">Customer Details</div>
            <div style="display:flex;flex-wrap:wrap;gap:8px 24px;">
                {f'<div><span style="color:#64748b;">Name:</span> {sale.customer_name}</div>' if sale.customer_name else ''}
                {f'<div><span style="color:#64748b;">Phone:</span> {sale.customer_phone}</div>' if sale.customer_phone else ''}
                {f'<div><span style="color:#64748b;">Place:</span> {sale.customer_place}</div>' if sale.customer_place else ''}
                {f'<div><span style="color:#64748b;">Email:</span> {sale.customer_email}</div>' if sale.customer_email else ''}
            </div>
        </div>
        '''}

        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Product</th>
                    <th>Qty</th>
                    <th>Price</th>
                    <th>Disc.</th>
                    <th>Tax</th>
                    <th>Total</th>
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
            <tr class="grand-total"><td>Grand Total</td><td style="text-align:right;">{currency}{sale.total:,.2f}</td></tr>
        </table>

        <div class="footer">
            Thank you for shopping with us!<br>
            {f"GSTIN: {store['store_gst']}" if store['store_gst'] else ""}
        </div>
        <script>
            window.onload = function() {{
                setTimeout(function() {{
                    window.print();
                }}, 500);
            }};
        </script>
    </body>
    </html>
    """
    return html

"""
Invoice Service — generate printable HTML invoice/receipt (Supports 58mm, 80mm, A4, and A5).
"""
from typing import Optional
from sqlalchemy.orm import Session, joinedload
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.setting import Setting
from fastapi import HTTPException


def number_to_indian_words(number: float) -> str:
    """Convert number to Indian Currency Words (Lakhs, Crores, Thousands)."""
    try:
        n = int(round(number))
        if n == 0:
            return "Zero Rupees Only"
        
        ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
                "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", 
                "Seventeen", "Eighteen", "Nineteen"]
        tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

        def helper(num: int) -> str:
            if num == 0:
                return ""
            elif num < 20:
                return ones[num] + " "
            elif num < 100:
                return tens[num // 10] + (" " + ones[num % 10] if num % 10 != 0 else "") + " "
            else:
                return ones[num // 100] + " Hundred " + helper(num % 100)

        result = ""
        crore = n // 10000000
        n %= 10000000
        if crore > 0:
            result += helper(crore) + "Crore "

        lakh = n // 100000
        n %= 100000
        if lakh > 0:
            result += helper(lakh) + "Lakh "

        thousand = n // 1000
        n %= 1000
        if thousand > 0:
            result += helper(thousand) + "Thousand "

        if n > 0:
            result += helper(n)

        return result.strip() + " Rupees Only"
    except Exception:
        return ""


def get_store_settings(db: Session) -> dict:
    """Load store profile settings from the database (with offline fallback)."""
    settings_dict = {}
    try:
        settings = db.query(Setting).all()
        settings_dict = {s.key: s.value for s in settings}
    except Exception:
        pass

    return {
        "store_name": settings_dict.get("store_name", "MOIRA LUXE"),
        "store_address": settings_dict.get("store_address", "Thuckalay, Kanyakumari"),
        "store_phone": settings_dict.get("store_phone", "8438353504"),
        "store_email": settings_dict.get("store_email", "moiraluxe@gmail.com"),
        "store_gst": settings_dict.get("store_gst", "33AAAAA0000A1Z5"),
        "currency_symbol": settings_dict.get("currency_symbol", "Rs."),
        "receipt_width": settings_dict.get("receipt_width", "A4"),
        "auto_print": settings_dict.get("auto_print", "true"),
    }


def generate_invoice_html(db: Session, sale_id: int, paper_format: Optional[str] = None) -> str:
    """Generate a printable HTML invoice for a sale (Supports A4, A5, 80mm, and 58mm)."""
    sale = db.query(Sale).options(joinedload(Sale.items).joinedload(SaleItem.product)).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    store = get_store_settings(db)
    currency = store.get("currency_symbol", "Rs.")
    chosen_format = (paper_format or store.get("receipt_width", "A4")).upper()

    from datetime import timedelta
    ist_time = (sale.created_at + timedelta(hours=5, minutes=30)) if sale.created_at else None
    created = ist_time.strftime("%d-%m-%Y  %I:%M %p") if ist_time else ""
    cashier = sale.user.name if sale.user else "Admin"

    # =========================================================================
    # A4 and A5 Full/Half Sheet Document Format (Epson EcoTank L6460 / Inkjet)
    # =========================================================================
    if "A4" in chosen_format or "A5" in chosen_format:
        is_a5 = "A5" in chosen_format
        page_size_css = "A5 landscape" if is_a5 else "A4 portrait"
        page_margin_css = "8mm" if is_a5 else "12mm"
        base_font_size = "12px" if is_a5 else "13.5px"

        rows_html = ""
        total_qty = 0
        for idx, item in enumerate(sale.items, 1):
            p_name = item.product.name if item.product else "Item"
            p_code = item.product.barcode if (item.product and item.product.barcode) else f"SKU-{idx:03d}"
            qty = item.quantity or 1
            total_qty += qty
            rate = item.unit_price or 0.0
            disc = item.discount or 0.0
            sub_amt = item.subtotal or (qty * rate - disc)

            rows_html += f"""
            <tr>
                <td style="text-align:center; padding:6px 8px; border:1px solid #cbd5e1;">{idx}</td>
                <td style="padding:6px 10px; border:1px solid #cbd5e1;">
                    <div style="font-weight:600; color:#0f172a;">{p_name}</div>
                    <div style="font-size:11px; color:#64748b;">Code: {p_code}</div>
                </td>
                <td style="text-align:center; padding:6px 8px; border:1px solid #cbd5e1; font-weight:600;">{qty}</td>
                <td style="text-align:right; padding:6px 8px; border:1px solid #cbd5e1;">{currency} {rate:,.2f}</td>
                <td style="text-align:right; padding:6px 8px; border:1px solid #cbd5e1; color:#dc2626;">{f"-{currency} {disc:,.2f}" if disc else "-"}</td>
                <td style="text-align:right; padding:6px 8px; border:1px solid #cbd5e1; font-weight:700;">{currency} {sub_amt:,.2f}</td>
            </tr>
            """

        amount_in_words = number_to_indian_words(sale.total)
        customer_name = sale.customer_name or "Walk-in Customer"
        customer_phone = sale.customer_phone or "-"
        customer_place = sale.customer_place or ""

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Tax Invoice - {sale.invoice_no}</title>
            <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/JsBarcode.all.min.js"></script>
            <style>
                * {{ margin:0; padding:0; box-sizing:border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
                body {{
                    background:#f8fafc;
                    color:#0f172a;
                    font-size:{base_font_size};
                    padding: 20px;
                }}
                .invoice-container {{
                    max-width: { '750px' if is_a5 else '820px' };
                    margin: 0 auto;
                    background: #ffffff;
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    padding: { '16px 20px' if is_a5 else '24px 30px' };
                    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
                }}
                .header-table {{ width:100%; border-collapse:collapse; margin-bottom:14px; }}
                .store-title {{ font-size:{ '20px' if is_a5 else '26px' }; font-weight:800; letter-spacing:1px; color:#0f172a; text-transform:uppercase; }}
                .store-sub {{ font-size:11.5px; color:#475569; margin-top:3px; line-height:1.4; }}
                .badge-invoice {{
                    display:inline-block;
                    background:#0f172a;
                    color:#ffffff;
                    font-weight:700;
                    font-size:12px;
                    padding:4px 12px;
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
                .info-grid td {{ padding: 8px 12px; vertical-align: top; font-size: 12px; }}
                .info-grid td:first-child {{ border-right: 1px solid #cbd5e1; width: 50%; }}
                .info-label {{ font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 700; margin-bottom: 2px; }}
                .info-val {{ font-weight: 600; color: #0f172a; }}
                
                .items-table {{ width:100%; border-collapse:collapse; margin-bottom:14px; }}
                .items-table th {{
                    background:#f1f5f9;
                    color:#334155;
                    font-size:11px;
                    font-weight:700;
                    text-transform:uppercase;
                    letter-spacing:0.5px;
                    padding:8px 8px;
                    border:1px solid #cbd5e1;
                }}
                
                .summary-table {{ width:100%; border-collapse:collapse; margin-top:8px; }}
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
                    margin-top: 16px;
                    padding-top: 12px;
                    border-top: 1px dashed #cbd5e1;
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-end;
                }}
                .terms {{ font-size: 10.5px; color: #64748b; max-width: 60%; line-height: 1.4; }}
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
            <div class="no-print" style="max-width:{'750px' if is_a5 else '820px'}; margin:0 auto 16px auto; display:flex; justify-content:space-between; align-items:center;">
                <button onclick="window.print()" style="background:#0f172a; color:#fff; border:none; padding:10px 22px; border-radius:6px; cursor:pointer; font-weight:700; font-size:13px; display:flex; align-items:center; gap:8px;">
                    🖨️ Print Invoice (Epson L6460)
                </button>
                <span style="font-size:12px; color:#64748b;">Paper format: <strong>{ 'A5 Half Sheet' if is_a5 else 'A4 Full Page' }</strong></span>
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
                            <div><strong>Bill No:</strong> {sale.invoice_no}</div>
                            <div><strong>Date & Time:</strong> {created}</div>
                            <div><strong>Payment Mode:</strong> <span style="text-transform:uppercase; color:#0f172a; font-weight:700;">{sale.payment_method}</span></div>
                            <div><strong>Cashier:</strong> {cashier}</div>
                        </td>
                        <td>
                            <div class="info-label">Billed To (Customer)</div>
                            <div class="info-val">{customer_name}</div>
                            <div>Phone: {customer_phone}</div>
                            {f"<div>Address: {customer_place}</div>" if customer_place else ""}
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
                            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:10px 12px; margin-top:4px;">
                                <div style="font-size:11px; text-transform:uppercase; color:#64748b; font-weight:700;">Amount in Words:</div>
                                <div style="font-weight:700; color:#0f172a; font-size:12px; margin-top:2px;">{amount_in_words}</div>
                                <div style="margin-top:6px; font-size:11.5px; color:#475569;">Total Items: <strong>{len(sale.items)}</strong> | Total Qty: <strong>{total_qty}</strong></div>
                            </div>
                        </td>
                        <td style="vertical-align:top; width:45%;">
                            <table class="summary-table">
                                <tr>
                                    <td style="color:#64748b;">Subtotal:</td>
                                    <td style="text-align:right; font-weight:600;">{currency} {sale.subtotal:,.2f}</td>
                                </tr>
                                {f"""<tr>
                                    <td style="color:#dc2626;">Discount:</td>
                                    <td style="text-align:right; font-weight:600; color:#dc2626;">-{currency} {sale.discount:,.2f}</td>
                                </tr>""" if sale.discount and sale.discount > 0 else ""}
                                {f"""<tr>
                                    <td style="color:#64748b;">GST / Tax:</td>
                                    <td style="text-align:right; font-weight:600;">+{currency} {sale.tax:,.2f}</td>
                                </tr>""" if sale.tax and sale.tax > 0 else ""}
                                <tr class="grand-total-row">
                                    <td>GRAND TOTAL:</td>
                                    <td style="text-align:right;">{currency} {sale.total:,.2f}</td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>

                <!-- Footer & Signature -->
                <div class="footer-box">
                    <div class="terms">
                        <strong>Terms & Conditions:</strong><br>
                        1. Goods once sold can be exchanged within 7 days with original bill.<br>
                        2. No cash refund on sold items.<br>
                        3. Thank you for shopping with <strong>{store['store_name']}</strong>!
                    </div>
                    <div class="sign-box">
                        <div class="sign-line"></div>
                        <div class="sign-label">For {store['store_name']}</div>
                        <div style="font-size:10px; color:#64748b;">Authorized Signatory</div>
                    </div>
                </div>
            </div>

            <script>
                window.onload = function() {{
                    if (typeof JsBarcode !== 'undefined') {{
                        JsBarcode("#barcode", "{sale.invoice_no}", {{
                            format: "CODE128",
                            width: 1.1,
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

    # =========================================================================
    # Thermal Roll Format (58mm / 80mm)
    # =========================================================================
    receipt_width = chosen_format
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

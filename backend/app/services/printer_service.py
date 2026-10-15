"""
Printer Service — Direct USB/Hardware RAW printing for TSPL (labels) and ESC/POS (receipts).
Bypasses the browser print preview dialog and prints directly to the physical printer.
"""
import sys
from datetime import datetime
from typing import List, Optional

try:
    import win32print
    HAS_WIN32PRINT = True
except ImportError:
    HAS_WIN32PRINT = False


def get_available_printers() -> List[str]:
    """Return all locally installed Windows printer names."""
    if not HAS_WIN32PRINT:
        return []
    try:
        printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
        return [p[2] for p in printers]
    except Exception as e:
        print(f"Error enumerating printers: {e}")
        return []


def get_default_printer_name() -> Optional[str]:
    """Get the current default printer name."""
    if not HAS_WIN32PRINT:
        return None
    try:
        return win32print.GetDefaultPrinter()
    except Exception:
        printers = get_available_printers()
        return printers[0] if printers else None


def send_raw_to_printer(raw_data: bytes, printer_name: Optional[str] = None) -> bool:
    """Send raw binary command bytes directly to the Windows printer spooler."""
    if not HAS_WIN32PRINT:
        raise RuntimeError("win32print is not available on this platform.")

    target_printer = printer_name or get_default_printer_name()
    if not target_printer:
        raise ValueError("No printer specified and no default printer found.")

    hPrinter = win32print.OpenPrinter(target_printer)
    try:
        # Start a raw print job
        hJob = win32print.StartDocPrinter(hPrinter, 1, ("Direct Label Job", None, "RAW"))
        try:
            win32print.StartPagePrinter(hPrinter)
            win32print.WritePrinter(hPrinter, raw_data)
            win32print.EndPagePrinter(hPrinter)
        finally:
            win32print.EndDocPrinter(hPrinter)
    finally:
        win32print.ClosePrinter(hPrinter)

    return True


def build_tspl_label(
    product_name: str,
    barcode: str,
    price: Optional[float] = None,
    store_name: str = "MOIRA LUXE",
    copies: int = 1,
    width_mm: int = 50,
    height_mm: int = 30,
    currency_symbol: str = "INR",
    show_price: bool = True,
    show_header: bool = True,
) -> bytes:
    """
    Generate standard TSPL (Taiwan Semiconductor / Xprinter Label) command bytes.
    Works natively on DEV 632-L58P, XP-235B, XP-245B, XP-365B label printers.
    """
    lines = [
        f"SIZE {width_mm} mm, {height_mm} mm",
        "GAP 2 mm, 0 mm",
        "DIRECTION 1",
        "CLS",
    ]

    # If showing header and price: Header on top-left/center, Price at top-right
    # Shop Name (shifted to very top margin y=0)
    if show_header and store_name:
        clean_store = store_name.replace('"', '').strip()
        lines.append(f'TEXT 25,0,"3",0,1,1,"{clean_store}"')

    # Price at top-right (y=0)
    if show_price and price is not None:
        price_str = f"Rs.{price:,.0f}" if price == int(price) else f"Rs.{price:,.2f}"
        lines.append(f'TEXT 280,0,"2",0,1,1,"{price_str}"')

    # Product Name
    clean_name = product_name[:26].replace('"', '').strip()
    lines.append(f'TEXT 25,28,"3",0,1,1,"{clean_name}"')

    # Barcode - expanded across label from left to right (x=20, narrow=3, wide=6, height=52)
    if barcode:
        clean_code = str(barcode).strip().replace('"', '')
        lines.append(f'BARCODE 20,70,"128",48,1,0,3,6,"{clean_code}"')

    lines.append(f"PRINT {max(1, copies)}")
    lines.append("")

    return "\r\n".join(lines).encode("ascii", errors="replace")


def build_tspl_receipt(
    invoice_no: str,
    items: list,
    subtotal: float,
    discount: float,
    total: float,
    store_name: str = "MOIRA LUXE",
    store_address: str = "Thuckalay",
    store_phone: str = "8438353504",
    currency_symbol: str = "Rs.",
    paper_width: str = "58mm",
    created_at: Optional[str] = None,
) -> bytes:
    """
    Generate the perfected full-width TSPL receipt with:
    - Prominent MOIRA LUXE header
    - Address: Thuckalay
    - Phone: 8438353504
    - Bill No & Date / Time
    - Edge-to-edge formatting and tight zero-waste height.
    """
    clean_store = (store_name or "MOIRA LUXE").replace('"', '').strip()
    address = (store_address or "Thuckalay").replace('"', '').strip()
    phone = (store_phone or "8438353504").replace('"', '').strip()
    clean_inv = str(invoice_no).replace('"', '').strip()
    curr = "Rs."
    sep = "--------------------------------------------"

    # Current date and time (e.g. "14-10-2026 12:45 PM")
    if created_at:
        date_str = str(created_at)
    else:
        date_str = datetime.now().strftime("%d-%m-%Y  %I:%M %p")

    # Calculate exact tight height in mm (dots / 8 at 203 DPI)
    # Header & Meta: ~260 dots, Each item: ~30 dots, Totals: ~90 dots, Footer: ~60 dots
    needed_dots = 270 + (len(items) * 30) + (30 if discount else 0) + 150
    height_mm = max(65, int(needed_dots / 8.0) + 4)

    commands = [
        f"SIZE 54 mm, {height_mm} mm",
        "GAP 0 mm, 0 mm",
        "DIRECTION 1",
        "CLS",
        f'TEXT 70,25,"3",0,2,2,"{clean_store}"',
        f'TEXT 135,78,"2",0,1,1,"{address}"',
        f'TEXT 105,102,"2",0,1,1,"Ph: {phone}"',
        f'TEXT 10,126,"2",0,1,1,"{sep}"',
        f'TEXT 15,148,"3",0,1,1,"Bill No: {clean_inv}"',
        f'TEXT 15,176,"2",0,1,1,"Date: {date_str}"',
        f'TEXT 10,202,"2",0,1,1,"{sep}"',
        f'TEXT 15,226,"3",0,1,1,"ITEM                  QTY     AMOUNT"',
        f'TEXT 10,254,"2",0,1,1,"{sep}"',
    ]

    y = 280
    for item in items:
        name = str(item.get("name", "Item"))[:20].replace('"', '').strip()
        qty = item.get("quantity", 1)
        price = float(item.get("price", 0))
        line = f"{name:<20}  {qty:>3}   {price:>8.2f}"
        commands.append(f'TEXT 15,{y},"3",0,1,1,"{line}"')
        y += 30

    commands.append(f'TEXT 10,{y},"2",0,1,1,"{sep}"')
    y += 25

    # Subtotal
    commands.append(f'TEXT 120,{y},"3",0,1,1,"Subtotal: {curr} {subtotal:,.2f}"')
    y += 30

    if discount:
        commands.append(f'TEXT 120,{y},"3",0,1,1,"Discount: -{curr} {discount:,.2f}"')
        y += 30

    # Total
    commands.append(f'TEXT 140,{y},"4",0,1,1,"TOTAL: {curr} {total:,.2f}"')
    y += 55

    # Footer
    commands.append(f'TEXT 45,{y},"3",0,1,1,"Thank you for shopping!"')
    commands.append("PRINT 1")
    commands.append("")

    return "\r\n".join(commands).encode("ascii", errors="replace")


def print_receipt_direct(
    invoice_no: str,
    items: list,
    subtotal: float,
    discount: float,
    total: float,
    store_name: str = "MOIRA LUXE",
    store_address: str = "Thuckalay",
    store_phone: str = "8438353504",
    currency_symbol: str = "Rs.",
    paper_width: str = "58mm",
    printer_name: Optional[str] = None,
    created_at: Optional[str] = None,
) -> bool:
    """
    Direct TSPL hardware print to the user's DEV 632 printer.
    Fast, crisp, and stops immediately without wasting paper.
    """
    raw_data = build_tspl_receipt(
        invoice_no=invoice_no,
        items=items,
        subtotal=subtotal,
        discount=discount,
        total=total,
        store_name=store_name,
        store_address=store_address,
        store_phone=store_phone,
        currency_symbol=currency_symbol,
        paper_width=paper_width,
        created_at=created_at,
    )
    target = printer_name or get_default_printer_name()
    return send_raw_to_printer(raw_data, target)


def print_receipt_gdi(
    invoice_no: str,
    items: list,
    subtotal: float,
    discount: float,
    total: float,
    store_name: str = "MOIRA LUXE",
    store_address: str = "",
    store_phone: str = "",
    currency_symbol: str = "Rs.",
    paper_width: str = "58mm",
    printer_name: Optional[str] = None
) -> bool:
    """
    Direct Windows native vector text printing.
    Uses native Windows GDI font rendering (No images/bitmaps), eliminating blank feeding
    and producing the crisp receipt layout shown in your photo.
    """
    if not HAS_WIN32PRINT:
        return False

    import win32ui
    import win32con

    target_printer = printer_name or get_default_printer_name()
    if not target_printer:
        raise ValueError("No printer specified and no default printer found.")

    import win32gui

    # Calculate required height based on content so printer stops immediately
    # Base height: header + meta + table header + totals + footer = ~320px
    # Each item = ~28px
    line_count = len(items)
    content_height_px = 350 + (line_count * 28)
    # At 203 DPI (8 dots per mm): 1 dot ~ 0.125 mm.
    # PaperLength in DEVMODE is in tenths of a millimeter (0.1 mm).
    # content_height_px / 8 = mm * 10 = tenths of mm. Add 5mm safety buffer.
    needed_tenths_mm = int((content_height_px / 8.0) * 10) + 50
    # Minimum 50mm (500), maximum 300mm (3000)
    needed_tenths_mm = max(500, min(needed_tenths_mm, 3000))

    hdc_handle = None
    try:
        h_printer = win32print.OpenPrinter(target_printer)
        try:
            printer_info = win32print.GetPrinter(h_printer, 2)
            devmode = printer_info['pDevMode']
            devmode.PaperWidth = 580
            devmode.PaperLength = needed_tenths_mm
            devmode.PaperSize = 0
            devmode.Fields = devmode.Fields | win32con.DM_PAPERWIDTH | win32con.DM_PAPERLENGTH | win32con.DM_PAPERSIZE
            hdc_handle = win32gui.CreateDC('WINSPOOL', target_printer, devmode)
        finally:
            win32print.ClosePrinter(h_printer)
    except Exception:
        pass

    if hdc_handle:
        hdc = win32ui.CreateDCFromHandle(hdc_handle)
    else:
        hdc = win32ui.CreateDC()
        hdc.CreatePrinterDC(target_printer)

    font_title = win32ui.CreateFont({
        "name": "Consolas",
        "height": 38,
        "weight": win32con.FW_BOLD
    })
    font_text = win32ui.CreateFont({
        "name": "Consolas",
        "height": 27,
        "weight": win32con.FW_NORMAL
    })
    font_bold = win32ui.CreateFont({
        "name": "Consolas",
        "height": 27,
        "weight": win32con.FW_BOLD
    })

    curr = "Rs."
    sep = "--------------------------------"

    try:
        hdc.StartDoc(f"Bill-{invoice_no}")
        hdc.StartPage()

        # Header
        hdc.SelectObject(font_title)
        clean_store = (store_name or "MOIRA LUXE").strip()
        hdc.TextOut(135, 15, clean_store)

        # Meta
        hdc.SelectObject(font_text)
        y = 60
        hdc.TextOut(20, y, sep)
        y += 28
        hdc.TextOut(20, y, f"Bill No: {invoice_no}")
        y += 28
        hdc.TextOut(20, y, sep)
        y += 28

        # Column Header
        hdc.TextOut(20, y, "ITEM             QTY      AMOUNT")
        y += 28
        hdc.TextOut(20, y, sep)
        y += 28

        # Items
        for item in items:
            name = str(item.get("name", "Item"))[:14]
            qty = str(item.get("quantity", 1))
            amt = f"{float(item.get('price', 0)):>8.2f}"
            line = f"{name:<14}   {qty:>3}   {amt}"
            hdc.TextOut(20, y, line)
            y += 28

        hdc.TextOut(20, y, sep)
        y += 28

        # Totals
        sub_str = f"Subtotal: {curr} {subtotal:,.2f}"
        hdc.TextOut(150, y, sub_str)
        y += 28

        if discount:
            disc_str = f"Discount: -{curr} {discount:,.2f}"
            hdc.TextOut(150, y, disc_str)
            y += 28

        hdc.SelectObject(font_bold)
        tot_str = f"TOTAL: {curr} {total:,.2f}"
        hdc.TextOut(175, y, tot_str)
        y += 45

        # Footer
        hdc.SelectObject(font_text)
        hdc.TextOut(85, y, "Thank you for shopping!")

        hdc.EndPage()
        hdc.EndDoc()
    finally:
        del hdc

    return True


def build_escpos_receipt(
    invoice_no: str,
    items: list,
    subtotal: float,
    discount: float,
    total: float,
    store_name: str = "MOIRA LUXE",
    store_address: str = "",
    store_phone: str = "",
    currency_symbol: str = "Rs.",
    paper_width: str = "80mm",
) -> bytes:
    """Generate standard TSPL bytes."""
    return build_tspl_receipt(
        invoice_no=invoice_no,
        items=items,
        subtotal=subtotal,
        discount=discount,
        total=total,
        store_name=store_name,
        store_address=store_address,
        store_phone=store_phone,
        currency_symbol=currency_symbol,
        paper_width=paper_width,
    )



"""
Printer Service — Direct USB/Hardware RAW printing for TSPL (labels) and ESC/POS (receipts).
Bypasses the browser print preview dialog and prints directly to the physical printer.
"""
import sys
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

    y = 20
    if show_header and store_name:
        clean_store = store_name.replace('"', '').strip()
        lines.append(f'TEXT 40,{y},"3",0,1,1,"{clean_store}"')
        y += 35

    clean_name = product_name[:20].replace('"', '').strip()
    lines.append(f'TEXT 40,{y},"3",0,1,1,"{clean_name}"')
    y += 38

    if show_price and price is not None:
        price_str = f"MRP: Rs. {price:,.2f}"
        lines.append(f'TEXT 40,{y},"3",0,1,2,"{price_str}"')
        y += 45

    if barcode:
        clean_code = str(barcode).strip().replace('"', '')
        lines.append(f'BARCODE 40,{y},"128",50,1,0,2,4,"{clean_code}"')

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
    store_address: str = "",
    store_phone: str = "",
    currency_symbol: str = "Rs.",
    paper_width: str = "58mm",
) -> bytes:
    """
    Generate compact, non-wasting TSPL receipt bytes.
    Calculates exact height dynamically to stop wasting paper and sets correct feed boundaries.
    """
    is_80mm = "80" in str(paper_width)
    width_mm = 72 if is_80mm else 48
    
    # Calculate exact tight height needed in dots (8 dots per mm at 203 DPI)
    # Header: ~100 dots, Each item: ~30 dots, Totals: ~90 dots, Footer: ~40 dots
    needed_dots = 160 + (len(items) * 30) + 120
    # Add barcode height if printing barcode
    needed_dots += 75
    height_mm = max(45, int(needed_dots / 8) + 4)

    curr = "Rs."
    commands = [
        f"SIZE {width_mm} mm, {height_mm} mm",
        "GAP 2 mm, 0 mm",
        "DIRECTION 1",
        "CLS",
    ]

    y = 15
    clean_store = (store_name or "MOIRA LUXE").replace('"', '').strip()
    commands.append(f'TEXT 20,{y},"3",0,1,1,"{clean_store}"')
    y += 32

    if store_phone:
        commands.append(f'TEXT 20,{y},"1",0,1,1,"Ph: {store_phone}"')
        y += 20

    clean_inv = str(invoice_no).replace('"', '').strip()
    commands.append(f'TEXT 20,{y},"2",0,1,1,"Bill: {clean_inv}"')
    y += 26

    sep = "------------------------------------------" if is_80mm else "--------------------------------"
    commands.append(f'TEXT 20,{y},"1",0,1,1,"{sep}"')
    y += 18

    # Table Header
    if is_80mm:
        commands.append(f'TEXT 20,{y},"2",0,1,1,"ITEM                  QTY       AMOUNT"')
    else:
        commands.append(f'TEXT 20,{y},"2",0,1,1,"ITEM            QTY     AMOUNT"')
    y += 24
    commands.append(f'TEXT 20,{y},"1",0,1,1,"{sep}"')
    y += 20

    name_len = 18 if is_80mm else 12
    for item in items:
        name = str(item.get("name", "Item"))[:name_len].replace('"', '').strip()
        qty = item.get("quantity", 1)
        price = item.get("price", 0)
        if is_80mm:
            line = f"{name:<18} {qty:>3}    {price:>8.2f}"
        else:
            line = f"{name:<12} {qty:>2}  {price:>7.2f}"
        commands.append(f'TEXT 20,{y},"2",0,1,1,"{line}"')
        y += 26

    commands.append(f'TEXT 20,{y},"1",0,1,1,"{sep}"')
    y += 20

    # Subtotal
    sub_line = f"Subtotal: {curr} {subtotal:,.2f}"
    commands.append(f'TEXT 20,{y},"2",0,1,1,"{sub_line}"')
    y += 24

    if discount:
        disc_line = f"Discount: -{curr} {discount:,.2f}"
        commands.append(f'TEXT 20,{y},"2",0,1,1,"{disc_line}"')
        y += 24

    tot_line = f"TOTAL: {curr} {total:,.2f}"
    commands.append(f'TEXT 20,{y},"3",0,1,1,"{tot_line}"')
    y += 34
    commands.append(f'TEXT 20,{y},"1",0,1,1,"{sep}"')
    y += 22

    if clean_inv:
        commands.append(f'BARCODE 20,{y},"128",38,1,0,2,3,"{clean_inv}"')
        y += 55

    commands.append(f'TEXT 20,{y},"1",0,1,1,"Thank you for shopping!"')
    commands.append("PRINT 1")
    commands.append("")

    return "\r\n".join(commands).encode("ascii", errors="replace")


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
    paper_width: str = "80mm",
    printer_name: Optional[str] = None
) -> bool:
    """
    Render a clean, crisp, pixel-perfect receipt using Windows GDI.
    Eliminates raw command printing and formats headers, item columns, and grand totals cleanly.
    """
    try:
        import win32ui
        import win32con
        from PIL import Image, ImageDraw, ImageFont, ImageWin
    except ImportError:
        # Fallback to raw if GDI components unavailable
        raw = build_tspl_receipt(invoice_no, items, subtotal, discount, total, store_name, store_address, store_phone, currency_symbol, paper_width)
        return send_raw_to_printer(raw, printer_name)

    is_80mm = "80" in str(paper_width)
    img_width = 576 if is_80mm else 384
    
    # Estimate height based on items
    base_height = 360 + len(items) * 32
    img = Image.new("RGB", (img_width, base_height), color="white")
    draw = ImageDraw.Draw(img)

    try:
        font_store = ImageFont.truetype("arialbd.ttf", 26 if is_80mm else 22)
        font_bold = ImageFont.truetype("arialbd.ttf", 17 if is_80mm else 15)
        font_reg = ImageFont.truetype("arial.ttf", 16 if is_80mm else 14)
        font_small = ImageFont.truetype("arial.ttf", 14 if is_80mm else 12)
    except Exception:
        font_store = font_bold = font_reg = font_small = ImageFont.load_default()

    margin = 14
    content_width = img_width - 2 * margin
    center_x = img_width // 2

    y = 12
    # Store Name & Header
    draw.text((center_x, y), store_name or "MOIRA LUXE", fill="black", font=font_store, anchor="mt")
    y += 34
    if store_address:
        draw.text((center_x, y), store_address, fill="black", font=font_small, anchor="mt")
        y += 18
    if store_phone:
        draw.text((center_x, y), f"Ph: {store_phone}", fill="black", font=font_small, anchor="mt")
        y += 18

    # Divider
    draw.line([(margin, y), (img_width - margin, y)], fill="black", width=1)
    y += 6

    # Meta
    draw.text((margin, y), f"Bill: {invoice_no}", fill="black", font=font_bold)
    y += 22
    draw.text((margin, y), "Cashier: Admin", fill="black", font=font_small)
    y += 20

    # Table Header
    draw.line([(margin, y), (img_width - margin, y)], fill="black", width=1)
    y += 5
    qty_x = int(img_width * 0.62)
    draw.text((margin, y), "ITEM", fill="black", font=font_bold)
    draw.text((qty_x, y), "QTY", fill="black", font=font_bold)
    draw.text((img_width - margin, y), "AMOUNT", fill="black", font=font_bold, anchor="ra")
    y += 22
    draw.line([(margin, y), (img_width - margin, y)], fill="black", width=1)
    y += 8

    # Items
    curr = "Rs."
    for item in items:
        name = str(item.get("name", "Item"))
        # shorten long names
        if len(name) > 22:
            name = name[:20] + ".."
        qty = str(item.get("quantity", 1))
        amt = f"{float(item.get('price', 0)):,.2f}"

        draw.text((margin, y), name, fill="black", font=font_reg)
        draw.text((qty_x + 8, y), qty, fill="black", font=font_reg)
        draw.text((img_width - margin, y), amt, fill="black", font=font_reg, anchor="ra")
        y += 26

    y += 4
    draw.line([(margin, y), (img_width - margin, y)], fill="black", width=1)
    y += 10

    # Totals
    draw.text((margin, y), "Subtotal:", fill="black", font=font_reg)
    draw.text((img_width - margin, y), f"{curr} {subtotal:,.2f}", fill="black", font=font_reg, anchor="ra")
    y += 24

    if discount:
        draw.text((margin, y), "Discount:", fill="black", font=font_reg)
        draw.text((img_width - margin, y), f"-{curr} {discount:,.2f}", fill="black", font=font_reg, anchor="ra")
        y += 24

    draw.line([(margin, y), (img_width - margin, y)], fill="black", width=1)
    y += 6
    draw.text((margin, y), "TOTAL:", fill="black", font=font_bold)
    draw.text((img_width - margin, y), f"{curr} {total:,.2f}", fill="black", font=font_bold, anchor="ra")
    y += 26
    draw.line([(margin, y), (img_width - margin, y)], fill="black", width=2)
    y += 16

    draw.text((center_x, y), "Thank you for shopping!", fill="black", font=font_small, anchor="mt")
    y += 35

    # Crop image to actual drawn height
    final_img = img.crop((0, 0, img_width, y))

    target_printer = printer_name or get_default_printer_name()
    if not target_printer:
        raise ValueError("No printer specified and no default printer found.")

    hDC = win32ui.CreateDC()
    hDC.CreatePrinterDC(target_printer)
    try:
        hDC.StartDoc(f"Receipt-{invoice_no}")
        hDC.StartPage()

        dib = ImageWin.Dib(final_img)
        # 1-to-1 draw coordinates to thermal head
        dib.draw(hDC.GetHandleOutput(), (10, 10, img_width + 10, y + 10))

        hDC.EndPage()
        hDC.EndDoc()
    finally:
        del hDC

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



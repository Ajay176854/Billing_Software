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
    Generate standard TSPL command bytes with top breathing space to prevent printing over the top edge.
    Works natively on DEV 632-L58P, XP-235B, XP-245B, XP-365B label printers.
    """
    lines = [
        f"SIZE {width_mm} mm, {height_mm} mm",
        "GAP 2 mm, 0 mm",
        "DIRECTION 1",
        "CLS",
    ]

    # Top breathing space (y > 0 so text doesn't touch or print over the top edge/peel gap)
    top_y = 28 if height_mm >= 30 else 20

    # Price string formatting
    price_str = ""
    if show_price and price is not None:
        price_str = f"Rs.{price:,.0f}" if price == int(price) else f"Rs.{price:,.2f}"

    # Header: Store Name centered in the middle with bold Font 4
    if show_header and store_name:
        clean_store = store_name.replace('"', '').strip()
        store_w = len(clean_store) * 24
        store_x = max(10, int(((width_mm * 8) - store_w) / 2))
        lines.append(f'TEXT {store_x},{top_y},"4",0,1,1,"{clean_store}"')

    # Line 2: Product Name on left and Price on right
    prod_y = top_y + (36 if height_mm >= 30 else 28)
    clean_name = product_name[:18].replace('"', '').strip()
    lines.append(f'TEXT 20,{prod_y},"3",0,1,1,"{clean_name}"')

    if show_price and price_str:
        price_x = max(230, (width_mm * 8) - (len(price_str) * 16) - 15)
        lines.append(f'TEXT {price_x},{prod_y},"3",0,1,1,"{price_str}"')

    # Line 3: Wide Barcode expanded across label (narrow=3, wide=6, height=48) for easy scanner detection
    barcode_y = prod_y + (36 if height_mm >= 30 else 28)
    barcode_h = 48 if height_mm >= 30 else 36
    if barcode:
        clean_code = str(barcode).strip().replace('"', '')
        lines.append(f'BARCODE 20,{barcode_y},"128",{barcode_h},1,0,3,6,"{clean_code}"')

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
    payment_method: Optional[str] = None,
) -> bytes:
    """
    Generate fully visible, perfectly aligned TSPL receipts:
    - Increased MOIRA LUXE store title font for clear prominence.
    - Generous breathing space between every section so nothing touches.
    - Guaranteed full visibility of item amounts, subtotal, discount, and grand total.
    - Prevents horizontal overflow on 58mm (384 dot) and 80mm thermal printers.
    - Tight zero-waste height calculation so printer cuts/stops cleanly.
    """
    clean_store = (store_name or "MOIRA LUXE").replace('"', '').strip()
    address = (store_address or "Thuckalay").replace('"', '').strip()
    phone = (store_phone or "8438353504").replace('"', '').strip()
    clean_inv = str(invoice_no).replace('"', '').strip()
    pay_mode = (payment_method or "CASH").upper().strip()
    curr = "Rs."

    is_80mm = "80" in str(paper_width)
    max_dots = 576 if is_80mm else 384
    page_w_mm = 72 if is_80mm else 58

    # Current date and time
    if created_at:
        date_str = str(created_at)
    else:
        date_str = datetime.now().strftime("%d-%m-%Y  %I:%M %p")

    commands = [
        f"SIZE {page_w_mm} mm, 80 mm",  # Placeholder, will update with exact height at end
        "GAP 0 mm, 0 mm",
        "DIRECTION 1",
        "CLS",
    ]

    margin_x = 18 if not is_80mm else 16

    if not is_80mm:
        # === 58mm THERMAL RECEIPT (CENTERED ON PHYSICAL ROLL) ===
        sep = "------------------------------"  # 30 chars, centered on roll

        # Section 1: Store Header (MOIRA LUXE big, bold, and centered)
        # Font "3" (12x24) with 2x2 scale = 24 dots per char. 10 chars = 240 dots.
        store_w = len(clean_store) * 24
        store_x = max(10, int((464 - store_w) / 2) - 18)
        commands.append(f'TEXT {store_x},20,"3",0,2,2,"{clean_store}"')
        header_bottom = 20 + 52

        # Combined Address & Phone line centered below store name (Font "2" ~11 dots/char)
        sub_info = f"{address} - {phone}".strip(" -")
        sub_w = len(sub_info) * 11
        sub_x = max(10, int((464 - sub_w) / 2) - 18)
        commands.append(f'TEXT {sub_x},{header_bottom + 8},"2",0,1,1,"{sub_info}"')

        # Section 2: Bill Meta (Divider with clear breathing room)
        meta_top = header_bottom + 36
        commands.append(f'TEXT {margin_x},{meta_top},"2",0,1,1,"{sep}"')
        commands.append(f'TEXT {margin_x},{meta_top + 26},"2",0,1,1,"Bill No: {clean_inv}"')
        commands.append(f'TEXT {margin_x},{meta_top + 52},"2",0,1,1,"Date   : {date_str}"')
        commands.append(f'TEXT {margin_x},{meta_top + 78},"2",0,1,1,"Payment: {pay_mode}"')
        commands.append(f'TEXT {margin_x},{meta_top + 104},"2",0,1,1,"{sep}"')

        # Section 3: Items Table Header (Clear separation)
        tbl_header_y = meta_top + 130
        commands.append(f'TEXT {margin_x},{tbl_header_y},"2",0,1,1,"ITEM          QTY       AMOUNT"')
        commands.append(f'TEXT {margin_x},{tbl_header_y + 26},"2",0,1,1,"{sep}"')

        # Items list (generous 28-dot line spacing so items never touch)
        y = tbl_header_y + 54
        for item in items:
            raw_name = str(item.get("name", "Item")).replace('"', '').strip()
            name_part = raw_name[:14]
            qty = item.get("quantity", 1)
            price = float(item.get("price", 0))

            # Exactly 30 characters: ITEM (14) + space + QTY (4) + space + AMOUNT (10)
            item_line = f"{name_part:<14} {qty:>4} {price:>10.2f}"
            commands.append(f'TEXT {margin_x},{y},"2",0,1,1,"{item_line}"')
            y += 28

            # If name is longer than 14 characters, print second line cleanly
            if len(raw_name) > 14:
                rem_name = raw_name[14:28]
                commands.append(f'TEXT {margin_x},{y},"2",0,1,1," {rem_name}"')
                y += 24

        # Section 4: Totals Section (Clear separation)
        commands.append(f'TEXT {margin_x},{y},"2",0,1,1,"{sep}"')
        y += 26

        # Subtotal (30 chars)
        sub_line = f"{'Subtotal:':<15} {curr}{subtotal:>11.2f}"
        commands.append(f'TEXT {margin_x},{y},"2",0,1,1,"{sub_line}"')
        y += 28

        # Discount (30 chars)
        if discount and float(discount) > 0:
            disc_line = f"{'Discount:':<15}-{curr}{float(discount):>10.2f}"
            commands.append(f'TEXT {margin_x},{y},"2",0,1,1,"{disc_line}"')
            y += 28

        commands.append(f'TEXT {margin_x},{y},"2",0,1,1,"{sep}"')
        y += 24

        # Grand Total in Font "3" (16x24 dots) — centered on roll
        tot_line = f"{'TOTAL:':<7} {curr}{total:>11.2f}"
        tot_w = len(tot_line) * 16
        tot_x = max(margin_x, int((464 - tot_w) / 2) - 18)
        commands.append(f'TEXT {tot_x},{y},"3",0,1,1,"{tot_line}"')
        y += 38

        commands.append(f'TEXT {margin_x},{y},"2",0,1,1,"{sep}"')
        y += 26

        # Section 5: Footer (Single centered footer with clear breathing room)
        footer = "Thank You For Shopping!"
        foot_w = len(footer) * 11
        foot_x = max(10, int((464 - foot_w) / 2) - 18)
        commands.append(f'TEXT {foot_x},{y},"2",0,1,1,"{footer}"')
        y += 38

    else:
        # === 80mm THERMAL RECEIPT (576 DOTS WIDTH) ===
        sep = "------------------------------------------"
        # Store name in Font "5" (32x48 dots) for large prominence
        store_x = max(margin_x, int((max_dots - (len(clean_store) * 32)) / 2))
        commands.append(f'TEXT {store_x},20,"5",0,1,1,"{clean_store}"')

        sub_info = f"{address} - {phone}".strip(" -")
        sub_x = max(margin_x, int((max_dots - (len(sub_info) * 16)) / 2))
        commands.append(f'TEXT {sub_x},80,"3",0,1,1,"{sub_info}"')

        commands.append(f'TEXT {margin_x},116,"3",0,1,1,"{sep}"')
        commands.append(f'TEXT {margin_x},148,"3",0,1,1,"Bill No: {clean_inv}"')
        commands.append(f'TEXT {margin_x},180,"3",0,1,1,"Date   : {date_str}"')
        commands.append(f'TEXT {margin_x},212,"3",0,1,1,"Payment: {pay_mode}"')
        commands.append(f'TEXT {margin_x},244,"3",0,1,1,"{sep}"')

        commands.append(f'TEXT {margin_x},276,"3",0,1,1,"ITEM                    QTY        AMOUNT"')
        commands.append(f'TEXT {margin_x},308,"3",0,1,1,"{sep}"')

        y = 340
        for item in items:
            raw_name = str(item.get("name", "Item")).replace('"', '').strip()
            name_part = raw_name[:20]
            qty = item.get("quantity", 1)
            price = float(item.get("price", 0))

            item_line = f"{name_part:<20} {qty:>5} {price:>13.2f}"
            commands.append(f'TEXT {margin_x},{y},"3",0,1,1,"{item_line}"')
            y += 34

            if len(raw_name) > 20:
                rem_name = raw_name[20:40]
                commands.append(f'TEXT {margin_x},{y},"3",0,1,1," {rem_name}"')
                y += 30

        commands.append(f'TEXT {margin_x},{y},"3",0,1,1,"{sep}"')
        y += 32

        sub_line = f"{'Subtotal:':<22} {curr}{subtotal:>15.2f}"
        commands.append(f'TEXT {margin_x},{y},"3",0,1,1,"{sub_line}"')
        y += 34

        if discount and float(discount) > 0:
            disc_line = f"{'Discount:':<22}-{curr}{float(discount):>14.2f}"
            commands.append(f'TEXT {margin_x},{y},"3",0,1,1,"{disc_line}"')
            y += 34

        commands.append(f'TEXT {margin_x},{y},"3",0,1,1,"{sep}"')
        y += 30

        tot_line = f"{'TOTAL:':<18} {curr}{total:>18.2f}"
        commands.append(f'TEXT {margin_x},{y},"4",0,1,1,"{tot_line}"')
        y += 48

        commands.append(f'TEXT {margin_x},{y},"3",0,1,1,"{sep}"')
        y += 30

        footer = "Thank You For Shopping!"
        foot_x = max(margin_x, int((max_dots - (len(footer) * 16)) / 2))
        commands.append(f'TEXT {foot_x},{y},"3",0,1,1,"{footer}"')
        y += 40

    # Calculate exact height in mm
    height_mm = max(60, int((y + 30) / 8.0) + 2)
    commands[0] = f"SIZE {page_w_mm} mm, {height_mm} mm"

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
    payment_method: Optional[str] = None,
) -> bool:
    """
    Direct TSPL hardware print to the user's DEV 632 / Xprinter / thermal receipt printer.
    Fast, crisp, 100% visible amounts, and stops immediately without wasting paper.
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
        payment_method=payment_method,
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
        store_x = max(10, int((384 - (len(clean_store) * 19)) / 2))
        hdc.TextOut(store_x, 15, clean_store)

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
        hdc.TextOut(30, y, sub_str)
        y += 28

        if discount:
            disc_str = f"Discount: -{curr} {discount:,.2f}"
            hdc.TextOut(30, y, disc_str)
            y += 28

        hdc.SelectObject(font_bold)
        tot_str = f"TOTAL: {curr} {total:,.2f}"
        hdc.TextOut(30, y, tot_str)
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



"""
Printer Service — Direct USB/Hardware RAW printing for TSPL (labels) and ESC/POS (receipts).
Bypasses the browser print preview dialog and prints directly to the physical printer.
"""
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
    width_mm: float = 50,
    height_mm: float = 30,
    currency_symbol: str = "INR",
    show_price: bool = True,
    show_header: bool = True,
    label_type: Optional[str] = None,
    show_qr: bool = False,
    enabled_columns: Optional[List[int]] = None,
) -> bytes:
    """
    Generate standard TSPL command bytes with top breathing space to prevent printing over the top edge.
    Works natively on DEV 632-L58P, XP-235B, XP-245B, XP-365B, Seznik Josh/Tej label printers.
    Supports:
    - Normal Label: Standard rectangular labels (50x30, 50x25, 40x30)
    - Tagging Label: Seznik 14.3mm x 100mm Jewellery Dumbbell 3-Up tags (Landscape with middle divider |)
    """
    is_tagging = (label_type == "tagging") or (label_type != "normal" and width_mm <= 20 and height_mm >= 70)

    # Special handling for Seznik 14.3mm x 100mm Jewellery Dumbbell Tag (3-Up Multi-Column Roll)
    # The roll consists of 3 horizontal dumbbell tags side-by-side across a ~50mm web (each tag is 14.3mm x 100mm).
    if is_tagging:
        import math

        # Total printable width is 48-50mm (384 dots at 203 DPI)
        # Measured Seznik 3-Up physical track layout:
        # Col 0 (Left):   X = 1 to 105 (Center = 53)
        # Col 1 (Center): X = 139 to 243 (Center = 191)
        # Col 2 (Right):  X = 278 to 382 (Center = 330)
        col_starts = [1, 139, 278]
        CHAR_W = 10
        LABEL_W = 104

        lines = [
            "SIZE 50 mm, 100 mm",
            "GAP 2 mm, 0 mm",
            "DIRECTION 0",
            "DENSITY 11",
            "CLS",
        ]

        # Clean product name (max 18 chars in landscape)
        clean_name = product_name.strip().replace('"', "")[:18]

        # Clean store name (max 16 chars in landscape)
        clean_store = (store_name or "").strip().replace('"', "")[:16]

        # Format price to fit comfortably (e.g. "Rs. 26900/-")
        price_str = ""
        if show_price and price is not None:
            p_val = int(price) if price == int(price) else price
            price_str = f"Rs. {p_val}/-" if isinstance(p_val, int) else f"Rs. {p_val:.2f}/-"
            if len(price_str) > 13:
                price_str = f"Rs.{int(price)}"[:12]

        clean_code = str(barcode or "").strip().replace('"', "")[:10]

        # Filter active columns (0=Left, 1=Middle, 2=Right) to prevent paper waste
        active_cols = [c for c in enabled_columns if c in (0, 1, 2)] if enabled_columns else [0, 1, 2]
        if not active_cols:
            active_cols = [0, 1, 2]

        # Print selected horizontal stickers across the 3-up roll in FULL LANDSCAPE
        # Symmetrically balanced across the center fold (Y = 200):
        # - Front Half (Details: Y = 25 to 185): Fully contained BEFORE the fold
        # - Dashed Fold Line at Y = 200: Exact physical center where tag folds back-to-back
        # - Back Half (Barcode: Y = 225 to 365): Fully contained AFTER the fold
        for col_idx in range(3):
            if col_idx not in active_cols:
                continue  # Skip disabled column to save physical stickers & avoid paper waste
            col_x = col_starts[col_idx]

            # --- PART 1: Front Face Details (Y = 15 to 230) ---
            # Line 1: Store Name (e.g. Moira Luxe)
            # Line 2: Product Name (e.g. Antitarnish Bangle)
            # Line 3: Price (e.g. Rs. 280/-)
            if show_header and clean_store:
                lines.append(f'TEXT {col_x + 95},15,"2",90,1,1,"{clean_store}"')
                lines.append(f'TEXT {col_x + 65},15,"2",90,1,1,"{clean_name}"')
                if show_price and price_str:
                    lines.append(f'TEXT {col_x + 35},20,"2",90,1,1,"{price_str}"')
            else:
                lines.append(f'TEXT {col_x + 80},15,"2",90,1,1,"{clean_name}"')
                if show_price and price_str:
                    lines.append(f'TEXT {col_x + 45},20,"2",90,1,1,"{price_str}"')

            # --- Centered Fold Marks (Outer edge ticks at Y = 236) ---
            lines.append(f"BAR {col_x + 2},236,8,2")
            lines.append(f"BAR {col_x + 94},236,8,2")

            # --- PART 2: Back Face 2D QR Code Tag (Jewellery Industry Standard) ---
            # 84x84 dot QR code centered across 14.3mm flap + clean code text underneath
            # Instant 360-degree omnidirectional scanning from any angle
            if clean_code:
                lines.append(f'QRCODE {col_x + 10},265,M,4,A,0,"{clean_code}"')
                lines.append(f'TEXT {col_x + 60},365,"2",90,1,1,"{clean_code}"')

        # Number of 100mm rows to feed (each row contains 3 horizontal stickers)
        rows_to_print = max(1, math.ceil(copies / 3)) if copies > 1 else 1
        lines.append(f"PRINT {rows_to_print}")
        lines.append("")
        return "\r\n".join(lines).encode("ascii", errors="replace")

    # Standard rectangular label formatting (50x30, 50x25, 40x30)
    norm_w = 50.0 if (width_mm <= 20 and height_mm >= 70) else width_mm
    norm_h = 30.0 if (width_mm <= 20 and height_mm >= 70) else height_mm
    w_label = int(norm_w) if norm_w == int(norm_w) else norm_w
    h_label = int(norm_h) if norm_h == int(norm_h) else norm_h

    lines = [
        f"SIZE {w_label} mm, {h_label} mm",
        "GAP 2 mm, 0 mm",
        "DIRECTION 1",
        "CLS",
    ]

    # Top breathing space
    top_y = 38 if norm_h >= 30 else 26

    # Price string formatting — formatted with Rs. prefix and /- suffix (e.g. Rs. 98/-)
    price_str = ""
    if show_price and price is not None:
        try:
            p_val = float(price)
            if p_val.is_integer():
                price_str = f"Rs. {int(p_val)}/-"
            else:
                price_str = f"Rs. {p_val:,.2f}/-"
        except Exception:
            price_str = f"Rs. {price}/-"

    # Safe horizontal margins: 35 dots on left, 350 dots on right (DEV 632-L58P 384 dot head)
    left_margin = 35
    safe_right = min(350, int((norm_w * 8) - 25))

    # Row 1: Store Name on left & Price on Top Right Corner
    if show_header and store_name:
        clean_store = store_name.replace('"', '').strip()
        lines.append(f'TEXT {left_margin},{top_y},"3",0,1,1,"{clean_store}"')

    if show_price and price_str:
        # Font 3 (16x24 dots per char) for clear, bold top-right price display
        price_w = len(price_str) * 16
        price_x = max(180, safe_right - price_w)
        lines.append(f'TEXT {price_x},{top_y},"3",0,1,1,"{price_str}"')

    # Row 2: Full-Width Product Name (increased character capacity up to 26+ characters)
    prod_y = top_y + (34 if norm_h >= 30 else 28)
    clean_raw_name = product_name.replace('"', '').strip()
    if len(clean_raw_name) > 26:
        # Extra long product names use Font 1 (8x12 dots) fitting up to 38 characters
        clean_name = clean_raw_name[:38]
        lines.append(f'TEXT {left_margin},{prod_y},"1",0,1,1,"{clean_name}"')
    else:
        # Standard names up to 26 characters in bold Font 2 (12x20 dots)
        clean_name = clean_raw_name[:26]
        lines.append(f'TEXT {left_margin},{prod_y},"2",0,1,1,"{clean_name}"')

    # Row 3: Enlarged Barcode or QR Code (centered with comfortable left & right breathing space)
    print_w = min(384, int(norm_w * 8))
    barcode_y = prod_y + (30 if norm_h >= 30 else 24)
    barcode_h = 66 if norm_h >= 30 else 46
    if barcode:
        clean_code = str(barcode).strip().replace('"', '')
        if show_qr:
            qr_w = 96
            qr_x = max(15, int((print_w - qr_w) / 2))
            lines.append(f'QRCODE {qr_x},{barcode_y},M,4,A,0,"{clean_code}"')
        else:
            # Code 128 total module count: start(11) + data(len*11) + check(11) + stop(13) = len*11 + 35
            tot_modules = len(clean_code) * 11 + 35
            # Module width 2 with wide=5 expands the bar thickness and increases size
            narrow = 2
            wide = 5
            bc_w = tot_modules * narrow
            # Centered with comfortable left space (~65 dots = ~8.1 mm)
            bc_x = max(35, int((print_w - bc_w) / 2) - 15)
            lines.append(f'BARCODE {bc_x},{barcode_y},"128",{barcode_h},1,0,{narrow},{wide},"{clean_code}"')

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



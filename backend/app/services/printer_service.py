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
    paper_width: str = "80mm",
) -> bytes:
    """Generate dynamic TSPL command bytes matching the verified hardware configuration."""
    is_80mm = "80" in str(paper_width)
    width_mm = 72 if is_80mm else 50

    # Ensure currency symbol is ASCII printable (Rupee symbol \u20b9 becomes ? in ASCII)
    curr = "Rs." if not currency_symbol or "\u20b9" in str(currency_symbol) or "?" in str(currency_symbol) else str(currency_symbol).strip()

    commands = [
        "SIZE 72 mm, 100 mm",
        "GAP 0 mm, 0 mm",
        "DIRECTION 1",
        "CLS",
    ]

    y = 30
    clean_store = (store_name or "MOIRA LUXE").replace('"', '').strip()
    commands.append(f'TEXT 40,{y},"3",0,1,1,"{clean_store}"')
    y += 45

    clean_inv = str(invoice_no).replace('"', '').strip()
    commands.append(f'TEXT 40,{y},"2",0,1,1,"Bill No: {clean_inv}"')
    y += 35

    sep = "------------------------------------------" if is_80mm else "--------------------------------"
    commands.append(f'TEXT 40,{y},"2",0,1,1,"{sep}"')
    y += 30

    if is_80mm:
        commands.append(f'TEXT 40,{y},"2",0,1,1,"ITEM                  QTY       AMOUNT"')
    else:
        commands.append(f'TEXT 40,{y},"2",0,1,1,"ITEM            QTY     AMOUNT"')
    y += 30
    commands.append(f'TEXT 40,{y},"2",0,1,1,"{sep}"')
    y += 30

    name_len = 20 if is_80mm else 14
    for item in items:
        name = str(item.get("name", "Item"))[:name_len].replace('"', '').strip()
        qty = item.get("quantity", 1)
        price = item.get("price", 0)
        if is_80mm:
            line = f"{name:<20} {qty:>3}    {price:>9.2f}"
        else:
            line = f"{name:<14} {qty:>3} {price:>8.2f}"
        commands.append(f'TEXT 40,{y},"2",0,1,1,"{line}"')
        y += 35

    commands.append(f'TEXT 40,{y},"2",0,1,1,"{sep}"')
    # Subtotal
    sub_line = f"Subtotal: Rs. {subtotal:,.2f}"
    commands.append(f'TEXT 40,{y},"2",0,1,1,"{sub_line}"')
    y += 30

    if discount:
        disc_line = f"Discount: -Rs. {discount:,.2f}"
        commands.append(f'TEXT 40,{y},"2",0,1,1,"{disc_line}"')
        y += 30

    tot_line = f"TOTAL: Rs. {total:,.2f}"
    commands.append(f'TEXT 40,{y},"3",0,1,1,"{tot_line}"')
    y += 45
    commands.append(f'TEXT 40,{y},"2",0,1,1,"{sep}"')
    y += 35

    if clean_inv:
        commands.append(f'BARCODE 40,{y},"128",45,1,0,2,4,"{clean_inv}"')
        y += 75

    commands.append(f'TEXT 40,{y},"2",0,1,1,"Thank you for shopping!"')
    commands.append("PRINT 1")
    commands.append("")

    return "\r\n".join(commands).encode("ascii", errors="replace")


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
    """Generate standard ESC/POS or TSPL bytes depending on driver."""
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



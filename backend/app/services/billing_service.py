"""
Billing Service — Core atomic billing logic.
TRD §13: Transaction & Data Integrity.

The complete_sale function performs the entire billing operation
inside a single database transaction:
1. Validate all cart items have sufficient stock.
2. Create sale record with unique invoice number.
3. Create sale_items records.
4. Decrement products.stock_qty for each item.
5. Create stock_transactions for each item.
6. Commit atomically; rollback on any failure.
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from fastapi import HTTPException, status

from app.models.product import Product
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.stock_transaction import StockTransaction
from app.models.setting import Setting
from app.schemas.sale import BillRequest


_cached_invoice_prefix: str = "INV"

def generate_invoice_number(db: Session) -> str:
    """Generate a unique invoice number: PREFIX-YYYYMMDD-NNNN using fast index lookup."""
    global _cached_invoice_prefix
    prefix = _cached_invoice_prefix

    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # Fast indexed lookup: find highest invoice today instead of counting entire table
    last_sale_today = (
        db.query(Sale.invoice_no)
        .filter(Sale.created_at >= today_start)
        .order_by(Sale.id.desc())
        .first()
    )

    next_seq = 1
    if last_sale_today and last_sale_today[0]:
        try:
            # Format is PREFIX-YYYYMMDD-NNNN
            parts = str(last_sale_today[0]).split("-")
            if len(parts) >= 3:
                next_seq = int(parts[-1]) + 1
        except (ValueError, IndexError):
            next_seq = 1

    return f"{prefix}-{today_str}-{next_seq:04d}"


def complete_sale(db: Session, bill: BillRequest, user_id: int) -> Sale:
    """
    Complete a sale atomically with high-speed batch locking.
    """
    try:
        # Step 1: Batch validate all items and lock rows in a SINGLE query
        item_quantities = {item.product_id: item.quantity for item in bill.items}
        item_discounts = {item.product_id: item.discount for item in bill.items}
        product_ids = list(item_quantities.keys())

        if not product_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cart is empty."
            )

        # Single batch query with row-level locks
        locked_products = (
            db.query(Product)
            .filter(Product.id.in_(product_ids), Product.status == "active")
            .with_for_update(of=Product)
            .all()
        )
        product_map = {p.id: p for p in locked_products}

        cart_products = []
        for item in bill.items:
            product = product_map.get(item.product_id)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product ID {item.product_id} not found or inactive."
                )

            if product.stock_qty < item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for '{product.name}'. Available: {product.stock_qty}, Requested: {item.quantity}"
                )

            cart_products.append((product, item))

        # Step 2: Generate invoice number
        invoice_no = generate_invoice_number(db)

        # Step 3: Calculate totals and prepare sale items
        sale_items = []
        subtotal = 0.0
        total_tax = 0.0

        for product, item in cart_products:
            item_subtotal = product.selling_price * item.quantity
            item_discount = item.discount
            taxable_amount = item_subtotal - item_discount
            item_tax = round(taxable_amount * (product.tax_rate / 100), 2)

            sale_item = SaleItem(
                product_id=product.id,
                quantity=item.quantity,
                unit_price=product.selling_price,
                discount=item_discount,
                tax_rate=product.tax_rate,
                tax=item_tax,
                subtotal=round(taxable_amount + item_tax, 2),
            )
            sale_items.append(sale_item)

            subtotal += item_subtotal
            total_tax += item_tax

        # Apply bill-level discount
        bill_discount = bill.bill_discount
        total_item_discounts = sum(item.discount for item in bill.items)
        total_discount = total_item_discounts + bill_discount
        grand_total = round(subtotal - total_discount + total_tax, 2)

        # Step 4: Create sale record
        sale = Sale(
            invoice_no=invoice_no,
            user_id=user_id,
            subtotal=round(subtotal, 2),
            discount=round(total_discount, 2),
            tax=round(total_tax, 2),
            total=grand_total,
            payment_method=bill.payment_method,
            status="completed",
            notes=bill.notes,
            customer_name=bill.customer_name,
            customer_phone=bill.customer_phone,
            customer_place=bill.customer_place,
            customer_email=bill.customer_email,
        )
        db.add(sale)
        db.flush()  # Assign sale.id

        # Step 5: Add sale items and decrement stock in bulk
        stock_transactions = []
        for (product, item), sale_item in zip(cart_products, sale_items):
            sale_item.sale_id = sale.id
            db.add(sale_item)

            # Decrement stock (BR-03)
            product.stock_qty -= item.quantity

            # Create stock transaction (BR-06)
            stock_transactions.append(
                StockTransaction(
                    product_id=product.id,
                    type="SALE",
                    quantity=-item.quantity,
                    reference_id=invoice_no,
                    reason=f"Sale {invoice_no}",
                    user_id=user_id,
                )
            )

        db.add_all(stock_transactions)

        # Step 6: Commit atomically
        db.commit()

        # Invalidate in-memory cache so subsequent product listings reflect new stock
        try:
            from app.cache import cache
            cache.clear()
        except Exception:
            pass

        # Return sale and formatted items directly from memory
        from app.schemas.sale import SaleItemResponse
        sale_items_data = [
            SaleItemResponse(
                id=s_item.id or 0,
                product_id=prod.id,
                product_name=prod.name,
                product_barcode=prod.barcode,
                quantity=it.quantity,
                unit_price=prod.selling_price,
                discount=it.discount,
                tax_rate=prod.tax_rate,
                tax=round((prod.selling_price * it.quantity - it.discount) * (prod.tax_rate / 100), 2),
                subtotal=round((prod.selling_price * it.quantity - it.discount) + round((prod.selling_price * it.quantity - it.discount) * (prod.tax_rate / 100), 2), 2),
            )
            for (prod, it), s_item in zip(cart_products, sale_items)
        ]

        return sale, sale_items_data

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Billing failed: {str(e)}"
        )


def cancel_sale(db: Session, sale_id: int, user_id: int) -> Sale:
    """
    Cancel a completed sale and restore stock (BR-04).
    """
    try:
        sale = db.query(Sale).options(
            joinedload(Sale.user),
            joinedload(Sale.items).joinedload(SaleItem.product)
        ).filter(Sale.id == sale_id).first()
        if not sale:
            raise HTTPException(status_code=404, detail="Sale not found")

        if sale.status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel a sale with status '{sale.status}'"
            )

        # Restore stock for each item
        for item in sale.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                product.stock_qty += item.quantity

                # Create return stock transaction
                stock_txn = StockTransaction(
                    product_id=product.id,
                    type="RETURN",
                    quantity=item.quantity,
                    reference_id=sale.invoice_no,
                    reason=f"Sale cancelled: {sale.invoice_no}",
                    user_id=user_id,
                )
                db.add(stock_txn)

        sale.status = "cancelled"
        db.commit()
        db.refresh(sale)
        return sale

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Cancellation failed: {str(e)}"
        )

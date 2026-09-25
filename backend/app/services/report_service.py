"""
Report Service — business intelligence queries.
"""
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.product import Product
from app.models.category import Category
from app.models.stock_transaction import StockTransaction


def get_dashboard_stats(db: Session) -> dict:
    """Get dashboard overview statistics."""
    IST = timezone(timedelta(hours=5, minutes=30))
    today_start = datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0)

    # Today's sales
    today_result = db.query(
        func.coalesce(func.sum(Sale.total), 0),
        func.count(Sale.id)
    ).filter(
        Sale.created_at >= today_start,
        Sale.status == "completed"
    ).first()

    today_sales = float(today_result[0])
    today_bills = int(today_result[1])

    # Product counts
    total_products = db.query(func.count(Product.id)).filter(Product.status == "active").scalar() or 0

    low_stock_count = db.query(func.count(Product.id)).filter(
        Product.status == "active",
        Product.stock_qty > 0,
        Product.stock_qty <= Product.reorder_level
    ).scalar() or 0

    out_of_stock_count = db.query(func.count(Product.id)).filter(
        Product.status == "active",
        Product.stock_qty == 0
    ).scalar() or 0

    # Total inventory value (at purchase price)
    inventory_value = db.query(
        func.coalesce(func.sum(Product.stock_qty * Product.purchase_price), 0)
    ).filter(Product.status == "active").scalar() or 0

    # Recent 5 sales
    recent_sales = db.query(Sale).filter(
        Sale.status == "completed"
    ).order_by(Sale.created_at.desc()).limit(5).all()

    recent_sales_data = [
        {
            "id": s.id,
            "invoice_no": s.invoice_no,
            "total": s.total,
            "payment_method": s.payment_method,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in recent_sales
    ]

    # Top 5 products by quantity sold (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    top_products_query = db.query(
        Product.id,
        Product.name,
        func.coalesce(func.sum(SaleItem.quantity), 0).label("total_sold"),
        func.coalesce(func.sum(SaleItem.subtotal), 0).label("total_revenue"),
    ).join(SaleItem, SaleItem.product_id == Product.id).join(
        Sale, Sale.id == SaleItem.sale_id
    ).filter(
        Sale.status == "completed",
        Sale.created_at >= thirty_days_ago,
    ).group_by(Product.id, Product.name).order_by(
        func.sum(SaleItem.quantity).desc()
    ).limit(5).all()

    top_products_data = [
        {
            "product_id": p.id,
            "product_name": p.name,
            "total_sold": int(p.total_sold),
            "total_revenue": float(p.total_revenue),
        }
        for p in top_products_query
    ]

    # Payment method summary (today)
    payment_summary_query = db.query(
        Sale.payment_method,
        func.sum(Sale.total),
        func.count(Sale.id),
    ).filter(
        Sale.created_at >= today_start,
        Sale.status == "completed"
    ).group_by(Sale.payment_method).all()

    payment_summary = [
        {"payment_method": p[0], "total_amount": float(p[1]), "count": int(p[2])}
        for p in payment_summary_query
    ]

    # Low stock items list (limit 5)
    low_stock_products_query = db.query(Product).filter(
        Product.status == "active",
        Product.stock_qty <= Product.reorder_level
    ).order_by(Product.stock_qty.asc()).limit(5).all()

    low_stock_products = [
        {
            "id": p.id,
            "name": p.name,
            "stock_qty": p.stock_qty,
            "reorder_level": p.reorder_level,
        }
        for p in low_stock_products_query
    ]

    return {
        "today_sales": today_sales,
        "today_bills": today_bills,
        "total_products": total_products,
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "total_inventory_value": float(inventory_value),
        "recent_sales": recent_sales_data,
        "top_products": top_products_data,
        "payment_summary": payment_summary,
        "low_stock_products": low_stock_products,
    }


def get_sales_by_date_range(db: Session, start_date: datetime, end_date: datetime) -> list:
    """Get daily sales summary for a date range."""
    # Offset by IST (+5:30) so func.date correctly groups by the local date
    local_created_at = Sale.created_at + timedelta(hours=5, minutes=30)
    
    sales = db.query(
        func.date(local_created_at).label("date"),
        func.sum(Sale.total).label("total_sales"),
        func.count(Sale.id).label("total_bills"),
        func.sum(Sale.discount).label("total_discount"),
        func.sum(Sale.tax).label("total_tax"),
    ).filter(
        Sale.created_at >= start_date,
        Sale.created_at <= end_date,
        Sale.status == "completed",
    ).group_by(func.date(local_created_at)).order_by(func.date(local_created_at)).all()

    return [
        {
            "date": str(s.date),
            "total_sales": float(s.total_sales),
            "total_bills": int(s.total_bills),
            "total_discount": float(s.total_discount),
            "total_tax": float(s.total_tax),
        }
        for s in sales
    ]


def get_product_sales_report(db: Session, start_date: datetime = None, end_date: datetime = None) -> list:
    """Get product-wise sales report."""
    query = db.query(
        Product.id,
        Product.name,
        Product.barcode,
        func.coalesce(func.sum(SaleItem.quantity), 0).label("total_qty_sold"),
        func.coalesce(func.sum(SaleItem.subtotal), 0).label("total_revenue"),
    ).join(SaleItem, SaleItem.product_id == Product.id).join(
        Sale, Sale.id == SaleItem.sale_id
    ).filter(Sale.status == "completed")

    if start_date:
        query = query.filter(Sale.created_at >= start_date)
    if end_date:
        query = query.filter(Sale.created_at <= end_date)

    results = query.group_by(Product.id, Product.name, Product.barcode).order_by(
        func.sum(SaleItem.quantity).desc()
    ).all()

    return [
        {
            "product_id": r.id,
            "product_name": r.name,
            "barcode": r.barcode,
            "total_qty_sold": int(r.total_qty_sold),
            "total_revenue": float(r.total_revenue),
        }
        for r in results
    ]

def get_itemized_sales_report(db: Session, start_date: datetime = None, end_date: datetime = None) -> list:
    """Get itemized sales report (every single item sold with invoice details)."""
    local_created_at = Sale.created_at + timedelta(hours=5, minutes=30)
    
    query = db.query(
        local_created_at.label("local_time"),
        Sale.invoice_no,
        Product.name.label("product_name"),
        Product.barcode,
        SaleItem.quantity,
        SaleItem.unit_price.label("price"),
        SaleItem.tax,
        SaleItem.subtotal,
    ).join(SaleItem, Sale.id == SaleItem.sale_id).join(
        Product, SaleItem.product_id == Product.id
    ).filter(Sale.status == "completed")

    if start_date:
        query = query.filter(Sale.created_at >= start_date)
    if end_date:
        query = query.filter(Sale.created_at <= end_date)

    results = query.order_by(Sale.created_at.desc()).all()

    return [
        {
            "date": r.local_time.strftime("%Y-%m-%d %H:%M:%S") if r.local_time else None,
            "invoice_no": r.invoice_no,
            "product_name": r.product_name,
            "barcode": r.barcode,
            "quantity": int(r.quantity),
            "price": float(r.price),
            "tax": float(r.tax),
            "total": float(r.subtotal) + float(r.tax),
        }
        for r in results
    ]


def get_customer_traffic_report(db: Session, start_date: datetime = None, end_date: datetime = None) -> list:
    """Get customer traffic report: top customers by purchase frequency and volume."""
    query = db.query(
        Sale.customer_phone,
        Sale.customer_name,
        func.count(Sale.id).label("total_visits"),
        func.sum(Sale.total).label("total_spent"),
        func.max(Sale.created_at).label("last_visit")
    ).filter(
        Sale.status == "completed",
        Sale.customer_phone != None,
        Sale.customer_phone != ""
    )

    if start_date:
        query = query.filter(Sale.created_at >= start_date)
    if end_date:
        query = query.filter(Sale.created_at <= end_date)

    results = query.group_by(Sale.customer_phone, Sale.customer_name).order_by(
        func.sum(Sale.total).desc()
    ).all()

    return [
        {
            "customer_phone": r.customer_phone,
            "customer_name": r.customer_name,
            "total_visits": int(r.total_visits),
            "total_spent": float(r.total_spent),
            "last_visit": r.last_visit.isoformat() if r.last_visit else None,
        }
        for r in results
    ]

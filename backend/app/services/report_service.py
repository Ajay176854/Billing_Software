"""
Report Service — business intelligence queries.
"""
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.product import Product


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

    # Product counts and inventory value
    product_stats = db.query(
        func.count(Product.id).label('total'),
        func.sum(case(((Product.stock_qty == 0), 1), else_=0)).label('out_of_stock'),
        func.sum(case(((Product.stock_qty > 0) & (Product.stock_qty <= Product.reorder_level), 1), else_=0)).label('low_stock'),
        func.coalesce(func.sum(Product.stock_qty * Product.purchase_price), 0).label('inventory_value')
    ).filter(Product.status == "active").first()

    total_products = product_stats.total or 0
    out_of_stock_count = product_stats.out_of_stock or 0
    low_stock_count = product_stats.low_stock or 0
    inventory_value = product_stats.inventory_value or 0

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
    # Fetch only required columns
    query_results = db.query(
        Sale.id, Sale.created_at, Sale.total, Sale.discount, Sale.tax,
        SaleItem.quantity, Product.purchase_price
    ).outerjoin(
        SaleItem, Sale.id == SaleItem.sale_id
    ).outerjoin(
        Product, SaleItem.product_id == Product.id
    ).filter(
        Sale.created_at >= start_date,
        Sale.created_at <= end_date,
        Sale.status == "completed",
    ).all()

    daily_stats = {}
    
    for row in query_results:
        sale_id, created_at, total, discount, tax, quantity, purchase_price = row
        
        # Offset by IST (+5:30) 
        local_date = (created_at + timedelta(hours=5, minutes=30)).date()
        date_str = str(local_date)
        
        if date_str not in daily_stats:
            daily_stats[date_str] = {
                "total_sales": 0.0,
                "total_bills": set(),
                "total_discount": 0.0,
                "total_tax": 0.0,
                "total_cost": 0.0
            }
            
        stats = daily_stats[date_str]
        
        if sale_id not in stats["total_bills"]:
            stats["total_bills"].add(sale_id)
            stats["total_sales"] += float(total)
            stats["total_discount"] += float(discount)
            stats["total_tax"] += float(tax)
        
        if quantity and purchase_price is not None:
            stats["total_cost"] += float(quantity) * float(purchase_price)

    result = []
    for date_str, stats in daily_stats.items():
        result.append({
            "date": date_str,
            "total_sales": stats["total_sales"],
            "total_bills": len(stats["total_bills"]),
            "total_discount": stats["total_discount"],
            "total_tax": stats["total_tax"],
            "total_profit": stats["total_sales"] - stats["total_tax"] - stats["total_cost"],
        })
        
    return result


def get_product_sales_report(db: Session, start_date: datetime = None, end_date: datetime = None) -> list:
    """Get product-wise sales report."""
    query = db.query(
        Product.id,
        Product.name,
        Product.barcode,
        func.coalesce(func.sum(SaleItem.quantity), 0).label("total_qty_sold"),
        func.coalesce(func.sum(SaleItem.subtotal), 0).label("total_revenue"),
        func.coalesce(func.sum((SaleItem.unit_price * SaleItem.quantity) - SaleItem.discount - (Product.purchase_price * SaleItem.quantity)), 0).label("total_profit"),
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
            "total_profit": float(r.total_profit),
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
        ((SaleItem.unit_price * SaleItem.quantity) - SaleItem.discount - (Product.purchase_price * SaleItem.quantity)).label("profit")
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
            "profit": float(r.profit) if r.profit is not None else 0.0,
        }
        for r in results
    ]


def get_customer_traffic_report(db: Session, start_date: datetime = None, end_date: datetime = None) -> list:
    """Get customer traffic report: top customers by purchase frequency and volume."""
    query = db.query(
        Sale.customer_phone,
        Sale.customer_name,
        Sale.total,
        Sale.created_at
    ).filter(
        Sale.status == "completed",
        Sale.customer_phone.is_not(None),
        Sale.customer_phone != ""
    )

    if start_date:
        query = query.filter(Sale.created_at >= start_date)
    if end_date:
        query = query.filter(Sale.created_at <= end_date)

    sales = query.all()
    
    customers = {}
    for phone, name, total, created_at in sales:
        if phone not in customers:
            customers[phone] = {
                "names": set(),
                "total_visits": 0,
                "total_spent": 0.0,
                "last_visit": None,
            }
        
        c = customers[phone]
        if name:
            c["names"].add(name)
        c["total_visits"] += 1
        c["total_spent"] += float(total)
        
        if not c["last_visit"] or (created_at and created_at > c["last_visit"]):
            c["last_visit"] = created_at
            
    results = []
    for phone, data in customers.items():
        # Combine all names used for this phone number
        name_list = sorted(list(data["names"]))
        name_str = " / ".join(name_list) if name_list else "Unknown"
        results.append({
            "customer_phone": phone,
            "customer_name": name_str,
            "total_visits": data["total_visits"],
            "total_spent": data["total_spent"],
            "last_visit": data["last_visit"].isoformat() if data["last_visit"] else None
        })
        
    # Sort by total_spent descending
    results.sort(key=lambda x: x["total_spent"], reverse=True)
    return results


def get_monitoring_report(db: Session, period: str = "daily", group_by: str = "overall", start_date: datetime = None, end_date: datetime = None) -> list:
    """
    Get time-series monitoring data.
    period: 'daily' or 'monthly'
    group_by: 'overall' or 'product'
    """
    # Fetch only needed columns
    sales_query = db.query(
        Sale.id, Sale.created_at, Sale.total, Sale.tax,
        SaleItem.product_id, SaleItem.quantity, SaleItem.unit_price, SaleItem.discount,
        Product.name, Product.purchase_price
    ).outerjoin(
        SaleItem, Sale.id == SaleItem.sale_id
    ).outerjoin(
        Product, SaleItem.product_id == Product.id
    ).filter(Sale.status == "completed")
    
    if start_date:
        sales_query = sales_query.filter(Sale.created_at >= start_date)
    if end_date:
        sales_query = sales_query.filter(Sale.created_at <= end_date)
        
    sales = sales_query.order_by(Sale.created_at).all()
    
    results_map = {}
    
    # We need to deduplicate sale totals and taxes because of the join
    processed_sales = set()
    
    for row in sales:
        sale_id, created_at, total, tax, product_id, quantity, unit_price, discount, product_name, purchase_price = row
        local_time = created_at + timedelta(hours=5, minutes=30)
        
        if period == "monthly":
            period_str = local_time.strftime('%Y-%m')
        else:
            period_str = local_time.strftime('%Y-%m-%d')
            
        if group_by == "overall":
            if period_str not in results_map:
                results_map[period_str] = {
                    "total_sales": 0.0,
                    "total_bills": 0,
                    "total_tax": 0.0,
                    "total_cost": 0.0
                }
            r = results_map[period_str]
            
            if sale_id not in processed_sales:
                processed_sales.add(sale_id)
                r["total_sales"] += float(total)
                r["total_bills"] += 1
                r["total_tax"] += float(tax)
            
            if quantity and purchase_price is not None:
                r["total_cost"] += float(quantity) * float(purchase_price)
                    
        else: # group_by == "product"
            if not product_id:
                continue
                
            key = f"{period_str}_{product_id}"
            if key not in results_map:
                results_map[key] = {
                    "date": period_str,
                    "product_id": product_id,
                    "product_name": product_name,
                    "qty_sold": 0,
                    "revenue": 0.0,
                    "profit": 0.0
                }
            r = results_map[key]
            r["qty_sold"] += quantity
            revenue = float(unit_price * quantity) - float(discount)
            r["revenue"] += revenue
            cost = float(purchase_price * quantity)
            r["profit"] += (revenue - cost)
                
    if group_by == "overall":
        output = []
        for p_str, r in results_map.items():
            output.append({
                "date": p_str,
                "total_sales": r["total_sales"],
                "total_bills": r["total_bills"],
                "total_profit": r["total_sales"] - r["total_tax"] - r["total_cost"]
            })
        return output
    else:
        return list(results_map.values())

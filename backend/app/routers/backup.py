"""
Backup router — database export and download (Admin only).
Supports exporting all products, sales, and settings directly from Supabase to local laptop.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.auth import require_role
from app.models.product import Product
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.category import Category
from app.models.setting import Setting

router = APIRouter(prefix="/backup", tags=["Backup"])


@router.get("/export")
def export_store_data(db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    """
    Export all store data (products, categories, sales, settings)
    directly from Supabase to download as a JSON file on local laptop.
    """
    try:
        # 1. Fetch categories
        categories = db.query(Category).all()
        categories_data = [
            {"id": c.id, "name": c.name, "prefix": c.prefix, "status": c.status}
            for c in categories
        ]

        # 2. Fetch products
        products = db.query(Product).all()
        products_data = [
            {
                "id": p.id,
                "name": p.name,
                "barcode": p.barcode,
                "sku": p.sku,
                "category_id": p.category_id,
                "purchase_price": p.purchase_price,
                "selling_price": p.selling_price,
                "tax_rate": p.tax_rate,
                "stock_qty": p.stock_qty,
                "unit": p.unit,
                "status": p.status,
            }
            for p in products
        ]

        # 3. Fetch sales with items
        sales = db.query(Sale).options(joinedload(Sale.items)).order_by(Sale.id.desc()).all()
        sales_data = [
            {
                "id": s.id,
                "invoice_no": s.invoice_no,
                "subtotal": s.subtotal,
                "discount": s.discount,
                "tax": s.tax,
                "total": s.total,
                "payment_method": s.payment_method,
                "status": s.status,
                "customer_name": s.customer_name,
                "customer_phone": s.customer_phone,
                "customer_place": s.customer_place,
                "customer_email": s.customer_email,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "items": [
                    {
                        "product_id": item.product_id,
                        "quantity": item.quantity,
                        "unit_price": item.unit_price,
                        "discount": item.discount,
                        "tax": item.tax,
                        "subtotal": item.subtotal,
                    }
                    for item in s.items
                ],
            }
            for s in sales
        ]

        # 4. Settings
        settings_rows = db.query(Setting).all()
        settings_data = {s.key: s.value for s in settings_rows}

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        export_payload = {
            "store": settings_data.get("store_name", "MOIRA LUXE"),
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total_products": len(products_data),
            "total_sales": len(sales_data),
            "categories": categories_data,
            "products": products_data,
            "sales": sales_data,
            "settings": settings_data,
        }

        filename = f"moira_luxe_store_backup_{timestamp}.json"
        return JSONResponse(
            content=export_payload,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/list")
def list_backups(current_user=Depends(require_role("admin"))):
    """Compatibility endpoint."""
    return {"backups": []}


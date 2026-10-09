"""
Products router — product CRUD with barcode lookup.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models.product import Product
from app.models.stock_transaction import StockTransaction
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.cache import cache

router = APIRouter(prefix="/products", tags=["Products"])


def _product_to_response(product: Product) -> ProductResponse:
    """Convert ORM product to response schema."""
    return ProductResponse(
        id=product.id,
        barcode=product.barcode,
        sku=product.sku,
        name=product.name,
        category_id=product.category_id,
        category_name=product.category.name if product.category else None,
        purchase_price=product.purchase_price,
        selling_price=product.selling_price,
        tax_rate=product.tax_rate,
        stock_qty=product.stock_qty,
        reorder_level=product.reorder_level,
        unit=product.unit,
        status=product.status,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


@router.get("", response_model=List[ProductResponse])
def list_products(
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List products with optional search and filters."""
    cache_key = f"products_list_{search}_{category_id}_{status_filter}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    query = db.query(Product)

    if search:
        query = query.filter(
            or_(
                Product.name.ilike(f"%{search}%"),
                Product.barcode.ilike(f"%{search}%"),
                Product.sku.ilike(f"%{search}%"),
            )
        )

    if category_id:
        query = query.filter(Product.category_id == category_id)

    if status_filter:
        query = query.filter(Product.status == status_filter)
    else:
        query = query.filter(Product.status == "active")

    from sqlalchemy.orm import joinedload
    products = query.options(joinedload(Product.category)).order_by(Product.name).all()
    result = [_product_to_response(p) for p in products]
    cache.set(cache_key, result, ttl=300)  # 5 min cache
    return result


@router.get("/next-code")
def get_next_code(
    prefix: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Generate next unique barcode/SKU based on prefix or category."""
    actual_prefix = "PRD"

    if prefix:
        actual_prefix = prefix.strip().upper()
    elif category_id:
        from app.models.category import Category
        cat = db.query(Category).filter(Category.id == category_id).first()
        if cat and cat.prefix:
            actual_prefix = cat.prefix.strip().upper()
        elif cat:
            # Fallback: take first 3 letters of category name
            actual_prefix = "".join(c for c in cat.name if c.isalpha())[:3].upper()

    # Find highest number for this prefix
    like_pattern = f"{actual_prefix}-%"
    products = db.query(Product).filter(
        or_(Product.barcode.like(like_pattern), Product.sku.like(like_pattern))
    ).all()

    max_num = 0
    for p in products:
        for code in [p.barcode, p.sku]:
            if code and code.startswith(f"{actual_prefix}-"):
                try:
                    num = int(code.split("-")[1])
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass

    next_num = max_num + 1
    next_code = f"{actual_prefix}-{next_num:03d}"

    return {"prefix": actual_prefix, "next_code": next_code}


@router.get("/barcode/{barcode}", response_model=ProductResponse)
def lookup_barcode(barcode: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Fast barcode lookup for POS scanning."""
    cache_key = f"product_barcode_{barcode}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    product = db.query(Product).filter(
        or_(Product.barcode == barcode, Product.sku == barcode),
        Product.status == "active"
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail=f"No product found with barcode or SKU: {barcode}")

    result = _product_to_response(product)
    cache.set(cache_key, result, ttl=3600)  # 1 hour cache for barcode lookups
    return result


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Get a specific product."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _product_to_response(product)


@router.post("", response_model=ProductResponse)
def create_product(data: ProductCreate, db: Session = Depends(get_db), current_user=Depends(require_role("admin", "inventory"))):
    """Create a new product."""
    # Validate unique barcode (BR-01)
    if data.barcode:
        exists = db.query(Product).filter(Product.barcode == data.barcode).first()
        if exists:
            raise HTTPException(status_code=400, detail=f"Barcode '{data.barcode}' already exists")

    if data.sku:
        exists = db.query(Product).filter(Product.sku == data.sku).first()
        if exists:
            raise HTTPException(status_code=400, detail=f"SKU '{data.sku}' already exists")

    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)

    # Record a STOCK_IN transaction if initial stock was set
    if product.stock_qty > 0:
        txn = StockTransaction(
            product_id=product.id,
            type="STOCK_IN",
            quantity=product.stock_qty,
            reason="Initial stock",
            user_id=current_user.id,
        )
        db.add(txn)
        db.commit()

    cache.clear()  # Invalidate cache
    return _product_to_response(product)


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, data: ProductUpdate, db: Session = Depends(get_db), current_user=Depends(require_role("admin", "inventory"))):
    """Update product information."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = data.model_dump(exclude_unset=True)

    # Validate barcode uniqueness if changing
    if "barcode" in update_data and update_data["barcode"]:
        exists = db.query(Product).filter(
            Product.barcode == update_data["barcode"],
            Product.id != product_id
        ).first()
        if exists:
            raise HTTPException(status_code=400, detail=f"Barcode '{update_data['barcode']}' already exists")

    if "sku" in update_data and update_data["sku"]:
        exists = db.query(Product).filter(
            Product.sku == update_data["sku"],
            Product.id != product_id
        ).first()
        if exists:
            raise HTTPException(status_code=400, detail=f"SKU '{update_data['sku']}' already exists")

    for key, value in update_data.items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    cache.clear()  # Invalidate cache
    return _product_to_response(product)


@router.delete("/{product_id}", status_code=204)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin", "inventory"))
):
    """Soft-delete a product by setting status to inactive."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.status = "inactive"
    db.commit()
    cache.clear()  # Invalidate cache
    return None

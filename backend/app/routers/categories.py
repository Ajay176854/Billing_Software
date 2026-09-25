"""
Categories router — category CRUD.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse
from app.cache import cache

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=List[CategoryResponse])
def list_categories(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """List all active categories."""
    cache_key = "categories_list"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    cats = db.query(Category).filter(Category.status == "active").order_by(Category.name).all()
    result = [CategoryResponse.model_validate(c) for c in cats]
    cache.set(cache_key, result, ttl=300)
    return result


@router.post("", response_model=CategoryResponse)
def create_category(data: CategoryCreate, db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    """Create a new category."""
    exists = db.query(Category).filter(Category.name == data.name).first()
    if exists:
        raise HTTPException(status_code=400, detail="Category already exists")
    cat = Category(name=data.name, prefix=data.prefix)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    cache.clear()
    return CategoryResponse.model_validate(cat)


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(category_id: int, data: CategoryUpdate, db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    """Update a category."""
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    if data.name is not None:
        cat.name = data.name
    if data.prefix is not None:
        cat.prefix = data.prefix
    if data.status is not None:
        cat.status = data.status
    db.commit()
    db.refresh(cat)
    cache.clear()
    return CategoryResponse.model_validate(cat)


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    """Soft-delete a category by setting status to inactive."""
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    cat.status = "inactive"
    db.commit()
    cache.clear()
    return None

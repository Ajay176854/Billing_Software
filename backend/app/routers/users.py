"""
Users router — user management (Admin only).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.auth import require_role, hash_password
from app.models.user import User
from app.models.sale import Sale
from app.models.stock_transaction import StockTransaction
from app.schemas.user import UserCreate, UserUpdate, UserResponse, PasswordReset

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    """List all users."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [UserResponse.model_validate(u) for u in users]


@router.post("", response_model=UserResponse)
def create_user(data: UserCreate, db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    """Create a new user account."""
    clean_username = data.username.strip()
    # Check duplicate username
    if db.query(User).filter(User.username == clean_username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    # Clean email: treat empty or whitespace-only string as None so unique constraint does not fail
    clean_email = data.email.strip() if data.email and data.email.strip() else None

    if clean_email and db.query(User).filter(User.email == clean_email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    user = User(
        name=data.name.strip(),
        username=clean_username,
        email=clean_email,
        password_hash=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    """Get a specific user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    """Update user details."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.name is not None:
        user.name = data.name.strip()
    if data.email is not None:
        clean_email = data.email.strip() if data.email.strip() else None
        if clean_email and db.query(User).filter(User.email == clean_email, User.id != user_id).first():
            raise HTTPException(status_code=400, detail="Email already exists")
        user.email = clean_email
    if data.role is not None:
        user.role = data.role
    if data.status is not None:
        user.status = data.status

    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/{user_id}/reset-password")
def reset_password(user_id: int, data: PasswordReset, db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    """Reset a user's password."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"message": "Password reset successfully"}


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    """Delete a user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    try:
        # Reassign associated records to the admin performing the deletion to preserve history
        db.query(Sale).filter(Sale.user_id == user_id).update({"user_id": current_user.id})
        db.query(StockTransaction).filter(StockTransaction.user_id == user_id).update({"user_id": current_user.id})

        db.delete(user)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to delete user: {str(e)}")

    return {"message": "User deleted successfully"}

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas
from ..database import get_db
from .auth import get_current_active_user

router = APIRouter()

@router.post("/items", response_model=schemas.CartItem)
async def add_to_cart(
    cart_item: schemas.CartItemCreate,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Check if product exists and is approved
    product = db.query(models.Product).filter(
        models.Product.id == cart_item.product_id,
        models.Product.approval_status == models.ApprovalStatus.APPROVED
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found or not approved")
    
    # Check if product is in stock
    if product.stock_quantity < cart_item.quantity:
        raise HTTPException(status_code=400, detail="Not enough stock available")
    
    # Check if item already exists in cart
    existing_item = db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id,
        models.CartItem.product_id == cart_item.product_id
    ).first()
    
    if existing_item:
        # Update quantity
        existing_item.quantity += cart_item.quantity
        db.commit()
        db.refresh(existing_item)
        return existing_item
    
    # Create new cart item
    db_cart_item = models.CartItem(
        user_id=current_user.id,
        product_id=cart_item.product_id,
        quantity=cart_item.quantity
    )
    
    db.add(db_cart_item)
    db.commit()
    db.refresh(db_cart_item)
    
    return db_cart_item

@router.get("/", response_model=schemas.Cart)
async def read_cart(
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Get all cart items for current user
    cart_items = db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).all()
    
    # Calculate total
    total = 0
    for item in cart_items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if product:
            total += product.price * item.quantity
    
    return {"items": cart_items, "total": total}

@router.put("/items/{item_id}", response_model=schemas.CartItem)
async def update_cart_item(
    item_id: int,
    item_update: schemas.CartItemUpdate,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Get cart item
    cart_item = db.query(models.CartItem).filter(
        models.CartItem.id == item_id,
        models.CartItem.user_id == current_user.id
    ).first()
    
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    # Check if product has enough stock
    product = db.query(models.Product).filter(models.Product.id == cart_item.product_id).first()
    if not product or product.stock_quantity < item_update.quantity:
        raise HTTPException(status_code=400, detail="Not enough stock available")
    
    # Update quantity
    cart_item.quantity = item_update.quantity
    db.commit()
    db.refresh(cart_item)
    
    return cart_item

@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_cart(
    item_id: int,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Get cart item
    cart_item = db.query(models.CartItem).filter(
        models.CartItem.id == item_id,
        models.CartItem.user_id == current_user.id
    ).first()
    
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    # Delete cart item
    db.delete(cart_item)
    db.commit()
    
    return {"status": "success"}

@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Delete all cart items for current user
    db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).delete()
    db.commit()
    
    return {"status": "success"}

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from .. import models, schemas
from ..database import get_db
from .auth import get_current_active_user

router = APIRouter()

class CheckoutSummary(BaseModel):
    subtotal: float
    shipping: float
    tax: float
    total: float

@router.get("/", response_model=CheckoutSummary)
async def get_checkout_summary(
    shipping_method_id: int = Query(..., description="ID of the selected shipping method"),
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Calculate checkout summary including subtotal, shipping cost, tax, and total
    """
    # Get user's cart
    cart_items = db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).all()
    
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Calculate subtotal
    subtotal = 0
    for item in cart_items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if product:
            subtotal += product.price * item.quantity
    
    # Get shipping cost
    shipping_method = db.query(models.ShippingMethod).filter(
        models.ShippingMethod.id == shipping_method_id,
        models.ShippingMethod.is_active == True
    ).first()
    
    if not shipping_method:
        raise HTTPException(status_code=404, detail="Shipping method not found")
    
    shipping_cost = shipping_method.price
    
    # Calculate tax (default 10%)
    tax_rate = 0.1
    tax_amount = round(subtotal * tax_rate, 2)
    
    # Calculate total
    total = subtotal + shipping_cost + tax_amount
    
    return {
        "subtotal": subtotal,
        "shipping": shipping_cost,
        "tax": tax_amount,
        "total": total
    }

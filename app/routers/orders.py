from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import uuid

from .. import models, schemas
from ..database import get_db
from .auth import get_current_active_user

router = APIRouter()

@router.post("/", response_model=schemas.Order, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_request: schemas.OrderBase,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new order from the user's cart
    """
    # Get user's cart
    cart_items = db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).all()
    
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Verify shipping address exists and belongs to user
    shipping_address = db.query(models.UserAddress).filter(
        models.UserAddress.id == order_request.shipping_address_id,
        models.UserAddress.user_id == current_user.id
    ).first()
    
    if not shipping_address:
        raise HTTPException(status_code=404, detail="Shipping address not found")
    
    # Verify shipping method exists
    shipping_method = db.query(models.ShippingMethod).filter(
        models.ShippingMethod.id == order_request.shipping_method_id,
        models.ShippingMethod.is_active == True
    ).first()
    
    if not shipping_method:
        raise HTTPException(status_code=404, detail="Shipping method not found")
    
    # Verify payment method exists and belongs to user
    payment_method = db.query(models.PaymentMethod).filter(
        models.PaymentMethod.id == order_request.payment_method_id,
        models.PaymentMethod.user_id == current_user.id,
        models.PaymentMethod.is_active == True
    ).first()
    
    if not payment_method:
        raise HTTPException(status_code=404, detail="Payment method not found")
    
    # Calculate order totals
    subtotal = 0
    tax_amount = 0
    
    # Create shipping address JSON
    shipping_address_json = {
        "full_name": shipping_address.full_name,
        "address_line1": shipping_address.address_line1,
        "address_line2": shipping_address.address_line2,
        "city": shipping_address.city,
        "state": shipping_address.state,
        "country": shipping_address.country,
        "zip_code": shipping_address.zip_code,
        "phone_number": shipping_address.phone_number
    }
    
    # Create a new order
    order = models.Order(
        order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
        user_id=current_user.id,
        subtotal_amount=0,  # Will be updated after adding items
        total_amount=0,  # Will be updated after adding items
        tax_amount=0,  # Will be updated after adding items
        shipping_amount=shipping_method.price,
        status=models.OrderStatus.PENDING,
        payment_status=models.PaymentStatus.PENDING,
        payment_method=payment_method.method_type,
        shipping_method=shipping_method.name,
        shipping_address=str(shipping_address_json),  # Convert to string for storage
        billing_address=str(shipping_address_json)  # Using shipping address as billing address
    )
    
    db.add(order)
    db.flush()  # Flush to get the order ID
    
    # Add order items
    for cart_item in cart_items:
        product = db.query(models.Product).filter(models.Product.id == cart_item.product_id).first()
        
        if not product:
            continue  # Skip if product no longer exists
        
        # Calculate item total and tax
        item_price = product.price
        item_total = item_price * cart_item.quantity
        
        # Default tax rate (10%)
        tax_rate = 0.1
        item_tax = item_total * tax_rate
        
        # Create order item
        order_item = models.OrderItem(
            order_id=order.id,
            product_id=product.id,
            seller_id=product.seller_id,
            quantity=cart_item.quantity,
            price=item_price,
            total=item_total,
            tax_amount=item_tax
        )
        
        db.add(order_item)
        
        # Update order totals
        subtotal += item_total
        tax_amount += item_tax
    
    # Update order with calculated totals
    total_amount = subtotal + tax_amount + order.shipping_amount
    
    order.subtotal_amount = subtotal
    order.tax_amount = tax_amount
    order.total_amount = total_amount
    
    # Commit transaction
    db.commit()
    db.refresh(order)
    
    # Clear the user's cart
    db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).delete()
    db.commit()
    
    return order

@router.get("/", response_model=List[schemas.Order])
async def get_orders(
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all orders for the current user
    """
    orders = db.query(models.Order).filter(models.Order.user_id == current_user.id).all()
    return orders

@router.get("/{order_id}", response_model=schemas.Order)
async def get_order(
    order_id: int,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific order by ID
    """
    order = db.query(models.Order).filter(
        models.Order.id == order_id,
        models.Order.user_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return order

@router.put("/{order_id}/cancel", response_model=schemas.Order)
async def cancel_order(
    order_id: int,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Cancel an order
    """
    order = db.query(models.Order).filter(
        models.Order.id == order_id,
        models.Order.user_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if order can be cancelled
    if order.status not in [models.OrderStatus.PENDING, models.OrderStatus.PROCESSING]:
        raise HTTPException(status_code=400, detail="Order cannot be cancelled")
    
    # Update order status
    order.status = models.OrderStatus.CANCELLED
    db.commit()
    db.refresh(order)
    
    return order

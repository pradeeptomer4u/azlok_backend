from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import uuid
import json

from .. import models, schemas
from ..database import get_db
from .auth import get_current_active_user
from ..utils.email_service import EmailService
from ..utils.whatsapp_service import WhatsAppService

router = APIRouter()

@router.post("/", response_model=schemas.OrderResponse, status_code=status.HTTP_201_CREATED)
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
        item_tax = item_total * (product.tax_rate/100)
        item_tax = round(item_tax, 2)
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
    
    # Query the order again to get all relationships loaded
    order_with_details = db.query(models.Order).filter(models.Order.id == order.id).first()
    
    # Send email notification in background
    try:
        # Parse shipping address from JSON string
        shipping_addr = json.loads(order.shipping_address) if isinstance(order.shipping_address, str) else shipping_address_json
        
        # Prepare order items for email
        email_items = []
        for item in order_with_details.items:
            email_items.append({
                "product_name": item.product.name if item.product else "Unknown Product",
                "quantity": item.quantity,
                "price": float(item.price),
                "total": float(item.total)
            })
        
        print(f"[ORDER EMAIL] Attempting to send email for order #{order.order_number}")
        
        # Send email synchronously (required for Lambda - background tasks don't work)
        EmailService.send_email(
            recipient_email="pradeeptomer4u@gmail.com",
            subject=f"New Order Created - #{order.order_number}",
            template_name="order_created",
            template_data={
                "order_id": order.id,
                "order_number": order.order_number,
                "customer_name": current_user.full_name or current_user.username,
                "customer_email": current_user.email,
                "order_date": order.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "payment_method": order.payment_method,
                "shipping_method": order.shipping_method,
                "items": email_items,
                "subtotal": float(order.subtotal_amount),
                "tax_amount": float(order.tax_amount),
                "shipping_amount": float(order.shipping_amount),
                "total_amount": float(order.total_amount),
                "shipping_address": shipping_addr
            }
        )
        print(f"[ORDER EMAIL] Email sent successfully for order #{order.order_number}")
    except Exception as e:
        # Log error but don't fail the order creation
        print(f"[ORDER EMAIL ERROR] Failed to send order notification email: {str(e)}")
        import traceback
        print(f"[ORDER EMAIL ERROR] Traceback: {traceback.format_exc()}")
    
    # Send WhatsApp notification (synchronous for Lambda)
    try:
        print(f"[ORDER WHATSAPP] Attempting to send WhatsApp for order #{order.order_number}")
        
        # Send to a single WhatsApp number (you can configure this)
        whatsapp_number = "+917300551699"
        
        # Extract product names from email_items
        product_names = [item["product_name"] for item in email_items]
        
        # Get customer phone number
        customer_phone = current_user.phone or shipping_addr.get("phone_number", "N/A")
        
        result = WhatsAppService.send_order_notification(
            phone_number=whatsapp_number,
            order_number=order.order_number,
            customer_name=current_user.full_name or current_user.username,
            customer_phone=customer_phone,
            total_amount=float(order.total_amount),
            items_count=len(email_items),
            shipping_address=shipping_addr,
            product_names=product_names
        )
        
        if result:
            print(f"[ORDER WHATSAPP] WhatsApp sent successfully for order #{order.order_number}")
        else:
            print(f"[ORDER WHATSAPP] WhatsApp sending failed for order #{order.order_number}")
            
    except Exception as e:
        # Log error but don't fail the order creation
        print(f"[ORDER WHATSAPP ERROR] Failed to send WhatsApp notification: {str(e)}")
        import traceback
        print(f"[ORDER WHATSAPP ERROR] Traceback: {traceback.format_exc()}")
    
    return order_with_details

# Public endpoint to track an order by order number
@router.get("/track/{order_number}")
async def track_order_by_number(
    order_number: int,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Public endpoint to track an order by its order number
    This endpoint doesn't require authentication
    """
    # Try to find the order by order_number
    order = db.query(models.Order).filter(
        models.Order.id == order_number,
                models.Order.user_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail=f"Order #{order_number} not found")
    
    # Return the order details
    return order

@router.get("/")
async def get_orders(
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all orders for the current user
    """
    orders = db.query(models.Order).filter(models.Order.user_id == current_user.id).all()
    return orders


@router.get("/{order_id}")
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

    # Convert the order to a dict and add the missing fields
    order_dict = {
        "id": order.id,
        "order_number": order.order_number,
        "user_id": order.user_id,
        "subtotal_amount": order.subtotal_amount,
        "total_amount": order.total_amount,
        "tax_amount": order.tax_amount,
        "cgst_amount": order.cgst_amount,
        "sgst_amount": order.sgst_amount,
        "igst_amount": order.igst_amount,
        "shipping_amount": order.shipping_amount,
        "discount_amount": order.discount_amount,
        "status": order.status,
        "payment_status": order.payment_status,
        "payment_method": order.payment_method,
        "payment_details": order.payment_details,
        "shipping_address": order.shipping_address,
        "billing_address": order.billing_address,
        "shipping_method": order.shipping_method,
        "tracking_number": order.tracking_number,
        "notes": order.notes,
        "invoice_number": order.invoice_number,
        "invoice_date": order.invoice_date,
        "invoice_url": order.invoice_url,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        # Add the missing fields required by the schema
        "payment_method_id": None,
        "shipping_method_id": None,
        "shipping_address_id": None
    }

    return order_dict
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

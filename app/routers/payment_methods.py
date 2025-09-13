from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from sqlalchemy.sql.functions import current_user

from ..database import get_db
from ..models import PaymentMethod, User
from ..schemas import PaymentMethodBase, PaymentMethod as PaymentMethodSchema, PaymentMethodType
from .auth import get_current_active_user, get_admin_user

router = APIRouter()

@router.get("/", response_model=List[PaymentMethodSchema])
async def get_payment_methods(
    db: Session = Depends(get_db),
):
    """Get all payment methods for the current user for checkout"""
    # Get payment methods for checkout
    # First get user-specific payment methods
    
    # Then get system-wide payment methods (those with user_id = None)
    system_payment_methods = db.query(PaymentMethod).filter(
        PaymentMethod.user_id == None,
        PaymentMethod.is_active == True
    ).all()
    
    
    return system_payment_methods

@router.get("/{payment_method_id}", response_model=PaymentMethodSchema)
async def get_payment_method(
    payment_method_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific payment method by ID"""
    # Try to find user-specific payment method first
    payment_method = db.query(PaymentMethod).filter(
        PaymentMethod.id == payment_method_id,
        PaymentMethod.user_id == current_user.id,
        PaymentMethod.is_active == True
    ).first()
    
    # If not found, try to find system-wide payment method
    if not payment_method:
        payment_method = db.query(PaymentMethod).filter(
            PaymentMethod.id == payment_method_id,
            PaymentMethod.user_id == None,
            PaymentMethod.is_active == True
        ).first()
    
    if not payment_method:
        raise HTTPException(status_code=404, detail="Payment method not found")
    
    # Fix metadata field to ensure it's a dictionary
    if payment_method.payment_metadata is None:
        payment_method.payment_metadata = {}
    
    return payment_method

@router.post("/", response_model=PaymentMethodSchema, status_code=status.HTTP_201_CREATED)
async def create_payment_method(
    payment_method: PaymentMethodBase,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new payment method for the current user"""
    # Check if this is the first payment method for the user
    existing_methods = db.query(PaymentMethod).filter(
        PaymentMethod.user_id == current_user.id,
        PaymentMethod.is_active == True
    ).count()
    
    # If it's the first method, make it default
    if existing_methods == 0:
        payment_method.is_default = True
    
    # If this method is set as default, unset other defaults
    if payment_method.is_default:
        db.query(PaymentMethod).filter(
            PaymentMethod.user_id == current_user.id,
            PaymentMethod.is_default == True
        ).update({"is_default": False})
    
    # Create the payment method
    payment_data = payment_method.dict()
    db_payment_method = PaymentMethod(**payment_data, user_id=current_user.id)
    
    # Ensure payment_metadata is a dictionary
    if db_payment_method.payment_metadata is None:
        db_payment_method.payment_metadata = {}
        
    db.add(db_payment_method)
    db.commit()
    db.refresh(db_payment_method)
    
    return db_payment_method

@router.put("/{payment_method_id}", response_model=PaymentMethodSchema)
async def update_payment_method(
    payment_method_id: int,
    payment_method_update: PaymentMethodBase,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a payment method"""
    db_payment_method = db.query(PaymentMethod).filter(
        PaymentMethod.id == payment_method_id,
        PaymentMethod.user_id == current_user.id,
        PaymentMethod.is_active == True
    ).first()
    
    if not db_payment_method:
        raise HTTPException(status_code=404, detail="Payment method not found")
    
    # If this method is being set as default, unset other defaults
    if payment_method_update.is_default:
        db.query(PaymentMethod).filter(
            PaymentMethod.user_id == current_user.id,
            PaymentMethod.is_default == True,
            PaymentMethod.id != payment_method_id
        ).update({"is_default": False})
    
    # Update fields
    for key, value in payment_method_update.dict().items():
        if value is not None:
            setattr(db_payment_method, key, value)
    
    # Ensure payment_metadata is a dictionary
    if db_payment_method.payment_metadata is None:
        db_payment_method.payment_metadata = {}
    
    db_payment_method.updated_at = datetime.now()
    db.commit()
    db.refresh(db_payment_method)
    
    return db_payment_method

@router.delete("/{payment_method_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment_method(
    payment_method_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a payment method"""
    db_payment_method = db.query(PaymentMethod).filter(
        PaymentMethod.id == payment_method_id,
        PaymentMethod.user_id == current_user.id,
        PaymentMethod.is_active == True
    ).first()
    
    if not db_payment_method:
        raise HTTPException(status_code=404, detail="Payment method not found")
    
    # If this is the default method, find another method to make default
    if db_payment_method.is_default:
        next_method = db.query(PaymentMethod).filter(
            PaymentMethod.user_id == current_user.id,
            PaymentMethod.id != payment_method_id,
            PaymentMethod.is_active == True
        ).first()
        
        if next_method:
            next_method.is_default = True
    
    # Soft delete by setting is_active to False
    db_payment_method.is_active = False
    db_payment_method.updated_at = datetime.now()
    db.commit()
    
    return {"detail": "Payment method deleted"}

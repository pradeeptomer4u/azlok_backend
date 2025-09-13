from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from sqlalchemy.sql.functions import current_user

from ..database import get_db
from ..models import PaymentMethod, User, PaymentMethodType as PaymentMethodTypeEnum
from ..schemas import PaymentMethodBase, PaymentMethodType
from .auth import get_current_active_user, get_admin_user

# Custom response model for payment methods
class PaymentMethodResponse(BaseModel):
    id: int
    method_type: PaymentMethodType
    provider: str
    is_default: bool = False
    is_active: bool = True
    user_id: Optional[int] = None
    
    # Optional fields based on payment method type
    card_last_four: Optional[str] = None
    card_expiry_month: Optional[str] = None
    card_expiry_year: Optional[str] = None
    card_holder_name: Optional[str] = None
    upi_id: Optional[str] = None
    bank_name: Optional[str] = None
    account_last_four: Optional[str] = None
    account_holder_name: Optional[str] = None
    wallet_provider: Optional[str] = None
    wallet_id: Optional[str] = None
    
    class Config:
        from_attributes = True

router = APIRouter()

@router.get("/", response_model=List[PaymentMethodResponse])
async def get_payment_methods(
    db: Session = Depends(get_db)
):
    """Get all payment methods for checkout"""
    # Get system-wide payment methods (those with user_id = None)
    system_payment_methods = db.query(PaymentMethod).filter(
        PaymentMethod.user_id == None,
        PaymentMethod.is_active == True
    ).all()
    
    return system_payment_methods

@router.get("/{payment_method_id}", response_model=PaymentMethodResponse)
async def get_payment_method(
    payment_method_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific payment method by ID"""
    # Find payment method by ID
    payment_method = db.query(PaymentMethod).filter(
        PaymentMethod.id == payment_method_id,
        PaymentMethod.is_active == True
    ).first()
    
    # No need to search again, the first query already covers all cases
    
    if not payment_method:
        raise HTTPException(status_code=404, detail="Payment method not found")
    
    # No need to fix metadata field with our custom response model
    
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

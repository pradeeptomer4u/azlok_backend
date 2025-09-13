from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from ..database import get_db
from ..models import ShippingMethod
from ..schemas import ShippingMethodBase, ShippingMethod as ShippingMethodSchema
from .auth import get_current_active_user, get_admin_user

router = APIRouter(
    prefix="/shipping-methods",
    tags=["shipping"],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=List[ShippingMethodSchema])
async def get_shipping_methods(
    db: Session = Depends(get_db)
):
    """Get all available shipping methods"""
    # Create some default shipping methods if none exist
    shipping_methods = db.query(ShippingMethod).filter(ShippingMethod.is_active == True).all()
    
    if not shipping_methods:
        # Create default shipping methods
        default_methods = [
            ShippingMethod(
                name="Standard Shipping",
                description="Delivery within 3-5 business days",
                price=50.0,
                estimated_days="3-5 days",
                is_active=True
            ),
            ShippingMethod(
                name="Express Shipping",
                description="Delivery within 1-2 business days",
                price=100.0,
                estimated_days="1-2 days",
                is_active=True
            ),
            ShippingMethod(
                name="Same Day Delivery",
                description="Delivery within 24 hours (select areas only)",
                price=200.0,
                estimated_days="Same day",
                is_active=True
            )
        ]
        
        db.add_all(default_methods)
        db.commit()
        
        # Fetch the newly created methods
        shipping_methods = db.query(ShippingMethod).filter(ShippingMethod.is_active == True).all()
    
    return shipping_methods

@router.get("/{shipping_method_id}", response_model=ShippingMethodSchema)
async def get_shipping_method(
    shipping_method_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific shipping method by ID"""
    shipping_method = db.query(ShippingMethod).filter(
        ShippingMethod.id == shipping_method_id,
        ShippingMethod.is_active == True
    ).first()
    
    if not shipping_method:
        raise HTTPException(status_code=404, detail="Shipping method not found")
    
    return shipping_method

@router.post("/", response_model=ShippingMethodSchema, status_code=status.HTTP_201_CREATED)
async def create_shipping_method(
    shipping_method: ShippingMethodBase,
    db: Session = Depends(get_db),
    current_user = Depends(get_admin_user)
):
    """Create a new shipping method (Admin only)"""
    db_shipping_method = ShippingMethod(**shipping_method.dict())
    db.add(db_shipping_method)
    db.commit()
    db.refresh(db_shipping_method)
    return db_shipping_method

@router.put("/{shipping_method_id}", response_model=ShippingMethodSchema)
async def update_shipping_method(
    shipping_method_id: int,
    shipping_method_update: ShippingMethodBase,
    db: Session = Depends(get_db),
    current_user = Depends(get_admin_user)
):
    """Update a shipping method (Admin only)"""
    db_shipping_method = db.query(ShippingMethod).filter(ShippingMethod.id == shipping_method_id).first()
    
    if not db_shipping_method:
        raise HTTPException(status_code=404, detail="Shipping method not found")
    
    # Update fields
    for key, value in shipping_method_update.dict().items():
        setattr(db_shipping_method, key, value)
    
    db_shipping_method.updated_at = datetime.now()
    db.commit()
    db.refresh(db_shipping_method)
    
    return db_shipping_method

@router.delete("/{shipping_method_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shipping_method(
    shipping_method_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_admin_user)
):
    """Delete a shipping method (Admin only)"""
    db_shipping_method = db.query(ShippingMethod).filter(ShippingMethod.id == shipping_method_id).first()
    
    if not db_shipping_method:
        raise HTTPException(status_code=404, detail="Shipping method not found")
    
    # Soft delete by setting is_active to False
    db_shipping_method.is_active = False
    db_shipping_method.updated_at = datetime.now()
    db.commit()
    
    return {"detail": "Shipping method deleted"}

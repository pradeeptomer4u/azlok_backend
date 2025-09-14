from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from ..database import get_db
from ..models import ShippingMethod, User
from ..schemas import ShippingMethodBase, ShippingMethod as ShippingMethodSchema
from .auth import get_current_active_user, get_admin_user

router = APIRouter()

@router.get("/", response_model=List[ShippingMethodSchema], status_code=status.HTTP_200_OK)
async def get_shipping_methods(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all available shipping methods"""
    # Get all active shipping methods from the database
    print(current_user.id)
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

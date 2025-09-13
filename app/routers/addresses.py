from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from ..database import get_db
from ..models import UserAddress, User
from ..schemas import UserAddressBase, UserAddressCreate, UserAddressUpdate, UserAddress as UserAddressSchema
from .auth import get_current_active_user

router = APIRouter(
    prefix="/users/addresses",
    tags=["addresses"],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=List[UserAddressSchema])
async def get_user_addresses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all addresses for the current user"""
    addresses = db.query(UserAddress).filter(
        UserAddress.user_id == current_user.id,
        UserAddress.is_active == True
    ).all()
    
    # If no addresses exist, create a default one
    if not addresses:
        # Create a default address
        default_address = UserAddress(
            user_id=current_user.id,
            full_name=current_user.full_name,
            address_line1="123 Main Street",
            city="Mumbai",
            state="Maharashtra",
            country="India",
            zip_code="400001",
            phone_number=current_user.phone or "9876543210",
            is_default=True,
            is_active=True
        )
        
        db.add(default_address)
        db.commit()
        db.refresh(default_address)
        
        addresses = [default_address]
    
    return addresses

@router.post("/", response_model=UserAddressSchema, status_code=status.HTTP_201_CREATED)
async def create_user_address(
    address: UserAddressCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new address for the current user"""
    # If this address is set as default, unset other defaults
    if address.is_default:
        db.query(UserAddress).filter(
            UserAddress.user_id == current_user.id,
            UserAddress.is_default == True
        ).update({"is_default": False})
    
    # Create the address
    db_address = UserAddress(**address.dict(), user_id=current_user.id)
    db.add(db_address)
    db.commit()
    db.refresh(db_address)
    
    return db_address

@router.get("/{address_id}", response_model=UserAddressSchema)
async def get_user_address(
    address_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific address by ID"""
    address = db.query(UserAddress).filter(
        UserAddress.id == address_id,
        UserAddress.user_id == current_user.id,
        UserAddress.is_active == True
    ).first()
    
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    
    return address

@router.put("/{address_id}", response_model=UserAddressSchema)
async def update_user_address(
    address_id: int,
    address_update: UserAddressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an address"""
    db_address = db.query(UserAddress).filter(
        UserAddress.id == address_id,
        UserAddress.user_id == current_user.id,
        UserAddress.is_active == True
    ).first()
    
    if not db_address:
        raise HTTPException(status_code=404, detail="Address not found")
    
    # If this address is being set as default, unset other defaults
    if address_update.is_default:
        db.query(UserAddress).filter(
            UserAddress.user_id == current_user.id,
            UserAddress.is_default == True,
            UserAddress.id != address_id
        ).update({"is_default": False})
    
    # Update fields
    update_data = address_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_address, key, value)
    
    db_address.updated_at = datetime.now()
    db.commit()
    db.refresh(db_address)
    
    return db_address

@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_address(
    address_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an address"""
    db_address = db.query(UserAddress).filter(
        UserAddress.id == address_id,
        UserAddress.user_id == current_user.id,
        UserAddress.is_active == True
    ).first()
    
    if not db_address:
        raise HTTPException(status_code=404, detail="Address not found")
    
    # If this is the default address, find another address to make default
    if db_address.is_default:
        next_address = db.query(UserAddress).filter(
            UserAddress.user_id == current_user.id,
            UserAddress.id != address_id,
            UserAddress.is_active == True
        ).first()
        
        if next_address:
            next_address.is_default = True
    
    # Soft delete by setting is_active to False
    db_address.is_active = False
    db_address.updated_at = datetime.now()
    db.commit()
    
    return {"detail": "Address deleted"}

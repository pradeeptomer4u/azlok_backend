from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc, or_, and_
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import json
from decimal import Decimal

from .. import models, schemas, models_inventory, schemas_inventory
from ..database import get_db
from .auth import get_current_active_user, get_admin_user

router = APIRouter()

# Helper function to check admin or company permissions
async def get_admin_or_company_user(current_user: schemas.User = Depends(get_current_active_user)):
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.COMPANY]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins or company users can access this endpoint"
        )
    return current_user

# Raw Material / Inventory Item APIs
@router.post("/items", response_model=schemas_inventory.InventoryItem, status_code=status.HTTP_201_CREATED)
async def create_inventory_item(
    item: schemas_inventory.InventoryItemCreate,
    current_user: schemas.User = Depends(get_admin_or_company_user),
    db: Session = Depends(get_db)
):
    # Check if code already exists
    existing_item = db.query(models_inventory.InventoryItem).filter(models_inventory.InventoryItem.code == item.code).first()
    if existing_item:
        raise HTTPException(status_code=400, detail="Item with this code already exists")
    
    # Check if category exists if provided
    if item.category_id:
        category = db.query(models.Category).filter(models.Category.id == item.category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail=f"Category with id {item.category_id} not found")
    
    # Create inventory item
    db_item = models_inventory.InventoryItem(
        name=item.name,
        code=item.code,
        description=item.description,
        category_id=item.category_id,
        unit_of_measure=item.unit_of_measure,
        min_stock_level=item.min_stock_level,
        max_stock_level=item.max_stock_level,
        reorder_level=item.reorder_level,
        cost_price=item.cost_price,
        hsn_code=item.hsn_code,
        is_active=item.is_active,
        is_raw_material=item.is_raw_material,
        created_by=current_user.id
    )
    
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    
    return db_item

@router.get("/items", response_model=List[schemas_inventory.InventoryItem])
async def read_inventory_items(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    is_raw_material: Optional[bool] = None,
    is_active: Optional[bool] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc",
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(models_inventory.InventoryItem)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                models_inventory.InventoryItem.name.ilike(f"%{search}%"),
                models_inventory.InventoryItem.code.ilike(f"%{search}%"),
                models_inventory.InventoryItem.description.ilike(f"%{search}%")
            )
        )
    
    if category_id:
        query = query.filter(models_inventory.InventoryItem.category_id == category_id)
    
    if is_raw_material is not None:
        query = query.filter(models_inventory.InventoryItem.is_raw_material == is_raw_material)
    
    if is_active is not None:
        query = query.filter(models_inventory.InventoryItem.is_active == is_active)
    
    # Apply sorting
    if sort_by:
        if sort_by == "name":
            query = query.order_by(asc(models_inventory.InventoryItem.name) if sort_order == "asc" else desc(models_inventory.InventoryItem.name))
        elif sort_by == "code":
            query = query.order_by(asc(models_inventory.InventoryItem.code) if sort_order == "asc" else desc(models_inventory.InventoryItem.code))
        elif sort_by == "current_stock":
            query = query.order_by(asc(models_inventory.InventoryItem.current_stock) if sort_order == "asc" else desc(models_inventory.InventoryItem.current_stock))
        elif sort_by == "created_at":
            query = query.order_by(asc(models_inventory.InventoryItem.created_at) if sort_order == "asc" else desc(models_inventory.InventoryItem.created_at))
    
    items = query.offset(skip).limit(limit).all()
    return items

@router.get("/items/{item_id}", response_model=schemas_inventory.InventoryItem)
async def read_inventory_item(
    item_id: int,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    item = db.query(models_inventory.InventoryItem).filter(models_inventory.InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return item

@router.put("/items/{item_id}", response_model=schemas_inventory.InventoryItem)
async def update_inventory_item(
    item_id: int,
    item_update: schemas_inventory.InventoryItemUpdate,
    current_user: schemas.User = Depends(get_admin_or_company_user),
    db: Session = Depends(get_db)
):
    db_item = db.query(models_inventory.InventoryItem).filter(models_inventory.InventoryItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    
    # Check if category exists if provided
    if item_update.category_id:
        category = db.query(models.Category).filter(models.Category.id == item_update.category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail=f"Category with id {item_update.category_id} not found")
    
    # Update fields if provided
    update_data = item_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_item, key, value)
    
    db.commit()
    db.refresh(db_item)
    
    return db_item

@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inventory_item(
    item_id: int,
    current_user: schemas.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    db_item = db.query(models_inventory.InventoryItem).filter(models_inventory.InventoryItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    
    # Check if item is used in any bill of materials
    bom_items = db.query(models_inventory.BillOfMaterialItem).filter(models_inventory.BillOfMaterialItem.inventory_item_id == item_id).first()
    if bom_items:
        raise HTTPException(status_code=400, detail="Cannot delete item as it is used in bill of materials")
    
    # Check if item has any stock movements
    stock_movements = db.query(models_inventory.StockMovement).filter(models_inventory.StockMovement.inventory_item_id == item_id).first()
    if stock_movements:
        # Instead of deleting, mark as inactive
        db_item.is_active = False
        db.commit()
        return
    
    # Delete item if not used anywhere
    db.delete(db_item)
    db.commit()
    
    return

@router.get("/items/stock-status", response_model=schemas_inventory.StockStatus)
async def get_inventory_stock_status(
    is_raw_material: Optional[bool] = None,
    category_id: Optional[int] = None,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(models_inventory.InventoryItem)
    
    # Apply filters
    if is_raw_material is not None:
        query = query.filter(models_inventory.InventoryItem.is_raw_material == is_raw_material)
    
    if category_id:
        query = query.filter(models_inventory.InventoryItem.category_id == category_id)
    
    items = query.all()
    
    # Process items to add status
    result_items = []
    low_stock_count = 0
    critical_stock_count = 0
    
    for item in items:
        status = "normal"
        if item.current_stock <= item.reorder_level:
            status = "low"
            low_stock_count += 1
        if item.current_stock <= item.min_stock_level:
            status = "critical"
            critical_stock_count += 1
        
        result_items.append({
            "id": item.id,
            "name": item.name,
            "code": item.code,
            "current_stock": float(item.current_stock),
            "unit_of_measure": item.unit_of_measure,
            "min_stock_level": float(item.min_stock_level),
            "reorder_level": float(item.reorder_level),
            "status": status
        })
    
    return {
        "items": result_items,
        "low_stock_count": low_stock_count,
        "critical_stock_count": critical_stock_count
    }

# Stock Movement APIs
@router.post("/stock-movements", response_model=schemas_inventory.StockMovement, status_code=status.HTTP_201_CREATED)
async def create_stock_movement(
    movement: schemas_inventory.StockMovementCreate,
    current_user: schemas.User = Depends(get_admin_or_company_user),
    db: Session = Depends(get_db)
):
    # Check if inventory item exists
    inventory_item = db.query(models_inventory.InventoryItem).filter(models_inventory.InventoryItem.id == movement.inventory_item_id).first()
    if not inventory_item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    
    # Calculate total value if unit price is provided
    total_value = None
    if movement.unit_price is not None:
        total_value = movement.quantity * movement.unit_price
    
    # Create stock movement
    db_movement = models_inventory.StockMovement(
        inventory_item_id=movement.inventory_item_id,
        movement_type=movement.movement_type,
        quantity=movement.quantity,
        unit_price=movement.unit_price,
        total_value=total_value,
        reference_number=movement.reference_number,
        reference_type=movement.reference_type,
        reference_id=movement.reference_id,
        notes=movement.notes,
        performed_by=current_user.id
    )
    
    db.add(db_movement)
    
    # Update inventory item stock
    if movement.movement_type in [schemas_inventory.StockMovementType.PURCHASE, schemas_inventory.StockMovementType.RETURN]:
        inventory_item.current_stock += Decimal(str(movement.quantity))
    elif movement.movement_type in [schemas_inventory.StockMovementType.PRODUCTION, schemas_inventory.StockMovementType.SALES, schemas_inventory.StockMovementType.WASTAGE]:
        if inventory_item.current_stock < Decimal(str(movement.quantity)):
            raise HTTPException(status_code=400, detail="Insufficient stock")
        inventory_item.current_stock -= Decimal(str(movement.quantity))
    elif movement.movement_type == schemas_inventory.StockMovementType.ADJUSTMENT:
        # For adjustments, quantity can be positive or negative
        inventory_item.current_stock += Decimal(str(movement.quantity))
    
    db.commit()
    db.refresh(db_movement)
    
    return db_movement

@router.get("/stock-movements", response_model=List[schemas_inventory.StockMovement])
async def read_stock_movements(
    skip: int = 0,
    limit: int = 100,
    inventory_item_id: Optional[int] = None,
    movement_type: Optional[schemas_inventory.StockMovementType] = None,
    reference_type: Optional[str] = None,
    reference_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(models_inventory.StockMovement)
    
    # Apply filters
    if inventory_item_id:
        query = query.filter(models_inventory.StockMovement.inventory_item_id == inventory_item_id)
    
    if movement_type:
        query = query.filter(models_inventory.StockMovement.movement_type == movement_type)
    
    if reference_type:
        query = query.filter(models_inventory.StockMovement.reference_type == reference_type)
    
    if reference_id:
        query = query.filter(models_inventory.StockMovement.reference_id == reference_id)
    
    if start_date:
        query = query.filter(models_inventory.StockMovement.performed_at >= start_date)
    
    if end_date:
        query = query.filter(models_inventory.StockMovement.performed_at <= end_date)
    
    # Order by performed_at descending (newest first)
    query = query.order_by(desc(models_inventory.StockMovement.performed_at))
    
    movements = query.offset(skip).limit(limit).all()
    return movements

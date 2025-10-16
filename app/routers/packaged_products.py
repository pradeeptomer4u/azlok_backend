from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc, or_, and_
from typing import List, Optional, Dict, Any
from datetime import datetime, date

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

# Packaged Product APIs
@router.post("/", response_model=schemas_inventory.PackagedProduct, status_code=status.HTTP_201_CREATED)
async def create_packaged_product(
    packaged_product: schemas_inventory.PackagedProductCreate,
    current_user: schemas.User = Depends(get_admin_or_company_user),
    db: Session = Depends(get_db)
):
    # Check if product exists
    product = db.query(models.Product).filter(models.Product.id == packaged_product.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if a packaged product with the same size already exists for this product
    existing_package = db.query(models_inventory.PackagedProduct).filter(
        models_inventory.PackagedProduct.product_id == packaged_product.product_id,
        models_inventory.PackagedProduct.packaging_size == packaged_product.packaging_size,
        models_inventory.PackagedProduct.custom_size == packaged_product.custom_size
    ).first()
    
    if existing_package:
        raise HTTPException(status_code=400, detail="A packaged product with this size already exists for this product")
    
    # Create packaged product
    db_packaged_product = models_inventory.PackagedProduct(
        product_id=packaged_product.product_id,
        packaging_size=packaged_product.packaging_size,
        custom_size=packaged_product.custom_size,
        weight_value=packaged_product.weight_value,
        weight_unit=packaged_product.weight_unit,
        items_per_package=packaged_product.items_per_package,
        barcode=packaged_product.barcode,
        min_stock_level=packaged_product.min_stock_level,
        reorder_level=packaged_product.reorder_level,
        is_active=packaged_product.is_active
    )
    
    db.add(db_packaged_product)
    db.commit()
    db.refresh(db_packaged_product)
    
    return db_packaged_product

@router.get("/", response_model=List[schemas_inventory.PackagedProduct])
async def read_packaged_products(
    skip: int = 0,
    limit: int = 100,
    product_id: Optional[int] = None,
    packaging_size: Optional[schemas_inventory.PackagingSize] = None,
    is_active: Optional[bool] = None,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(models_inventory.PackagedProduct)
    
    # Apply filters
    if product_id:
        query = query.filter(models_inventory.PackagedProduct.product_id == product_id)
    
    if packaging_size:
        query = query.filter(models_inventory.PackagedProduct.packaging_size == packaging_size)
    
    if is_active is not None:
        query = query.filter(models_inventory.PackagedProduct.is_active == is_active)
    
    packaged_products = query.offset(skip).limit(limit).all()
    return packaged_products

@router.get("/{packaged_product_id}", response_model=schemas_inventory.PackagedProduct)
async def read_packaged_product(
    packaged_product_id: int,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    packaged_product = db.query(models_inventory.PackagedProduct).filter(models_inventory.PackagedProduct.id == packaged_product_id).first()
    if not packaged_product:
        raise HTTPException(status_code=404, detail="Packaged product not found")
    return packaged_product

@router.put("/{packaged_product_id}", response_model=schemas_inventory.PackagedProduct)
async def update_packaged_product(
    packaged_product_id: int,
    packaged_product_update: schemas_inventory.PackagedProductUpdate,
    current_user: schemas.User = Depends(get_admin_or_company_user),
    db: Session = Depends(get_db)
):
    db_packaged_product = db.query(models_inventory.PackagedProduct).filter(models_inventory.PackagedProduct.id == packaged_product_id).first()
    if not db_packaged_product:
        raise HTTPException(status_code=404, detail="Packaged product not found")
    
    # Update fields if provided
    update_data = packaged_product_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_packaged_product, key, value)
    
    db.commit()
    db.refresh(db_packaged_product)
    
    return db_packaged_product

@router.delete("/{packaged_product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_packaged_product(
    packaged_product_id: int,
    current_user: schemas.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    db_packaged_product = db.query(models_inventory.PackagedProduct).filter(models_inventory.PackagedProduct.id == packaged_product_id).first()
    if not db_packaged_product:
        raise HTTPException(status_code=404, detail="Packaged product not found")
    
    # Check if there are any movements for this packaged product
    movements = db.query(models_inventory.PackagedProductMovement).filter(models_inventory.PackagedProductMovement.packaged_product_id == packaged_product_id).first()
    if movements:
        # Instead of deleting, mark as inactive
        db_packaged_product.is_active = False
        db.commit()
        return
    
    # Delete if not used anywhere
    db.delete(db_packaged_product)
    db.commit()
    
    return

@router.post("/movements", response_model=schemas_inventory.PackagedProductMovement, status_code=status.HTTP_201_CREATED)
async def create_packaged_product_movement(
    movement: schemas_inventory.PackagedProductMovementCreate,
    current_user: schemas.User = Depends(get_admin_or_company_user),
    db: Session = Depends(get_db)
):
    # Check if packaged product exists
    packaged_product = db.query(models_inventory.PackagedProduct).filter(models_inventory.PackagedProduct.id == movement.packaged_product_id).first()
    if not packaged_product:
        raise HTTPException(status_code=404, detail="Packaged product not found")
    
    # Check if order exists if provided
    if movement.order_id:
        order = db.query(models.Order).filter(models.Order.id == movement.order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if order item exists if provided
    if movement.order_item_id:
        order_item = db.query(models.OrderItem).filter(models.OrderItem.id == movement.order_item_id).first()
        if not order_item:
            raise HTTPException(status_code=404, detail="Order item not found")
    
    # Create packaged product movement
    db_movement = models_inventory.PackagedProductMovement(
        packaged_product_id=movement.packaged_product_id,
        movement_type=movement.movement_type,
        quantity=movement.quantity,
        order_id=movement.order_id,
        order_item_id=movement.order_item_id,
        reference_number=movement.reference_number,
        reference_type=movement.reference_type,
        reference_id=movement.reference_id,
        notes=movement.notes,
        performed_by=current_user.id
    )
    
    db.add(db_movement)
    
    # Update packaged product stock
    if movement.movement_type in [schemas_inventory.StockMovementType.PRODUCTION, schemas_inventory.StockMovementType.RETURN]:
        packaged_product.current_stock += movement.quantity
    elif movement.movement_type in [schemas_inventory.StockMovementType.SALES, schemas_inventory.StockMovementType.WASTAGE]:
        if packaged_product.current_stock < movement.quantity:
            raise HTTPException(status_code=400, detail="Insufficient stock")
        packaged_product.current_stock -= movement.quantity
    elif movement.movement_type == schemas_inventory.StockMovementType.ADJUSTMENT:
        # For adjustments, quantity can be positive or negative
        packaged_product.current_stock += movement.quantity
    
    db.commit()
    db.refresh(db_movement)
    
    return db_movement

@router.get("/movements", response_model=List[schemas_inventory.PackagedProductMovement])
async def read_packaged_product_movements(
    skip: int = 0,
    limit: int = 100,
    packaged_product_id: Optional[int] = None,
    movement_type: Optional[schemas_inventory.StockMovementType] = None,
    order_id: Optional[int] = None,
    reference_type: Optional[str] = None,
    reference_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(models_inventory.PackagedProductMovement)
    
    # Apply filters
    if packaged_product_id:
        query = query.filter(models_inventory.PackagedProductMovement.packaged_product_id == packaged_product_id)
    
    if movement_type:
        query = query.filter(models_inventory.PackagedProductMovement.movement_type == movement_type)
    
    if order_id:
        query = query.filter(models_inventory.PackagedProductMovement.order_id == order_id)
    
    if reference_type:
        query = query.filter(models_inventory.PackagedProductMovement.reference_type == reference_type)
    
    if reference_id:
        query = query.filter(models_inventory.PackagedProductMovement.reference_id == reference_id)
    
    if start_date:
        query = query.filter(models_inventory.PackagedProductMovement.performed_at >= start_date)
    
    if end_date:
        query = query.filter(models_inventory.PackagedProductMovement.performed_at <= end_date)
    
    # Order by performed_at descending (newest first)
    query = query.order_by(desc(models_inventory.PackagedProductMovement.performed_at))
    
    movements = query.offset(skip).limit(limit).all()
    return movements

@router.get("/stock-status", response_model=schemas_inventory.PackagedProductStock)
async def get_packaged_product_stock_status(
    product_id: Optional[int] = None,
    packaging_size: Optional[schemas_inventory.PackagingSize] = None,
    is_active: Optional[bool] = True,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(models_inventory.PackagedProduct)
    
    # Apply filters
    if product_id:
        query = query.filter(models_inventory.PackagedProduct.product_id == product_id)
    
    if packaging_size:
        query = query.filter(models_inventory.PackagedProduct.packaging_size == packaging_size)
    
    if is_active is not None:
        query = query.filter(models_inventory.PackagedProduct.is_active == is_active)
    
    packaged_products = query.all()
    
    # Process items to add status and product name
    result_items = []
    low_stock_count = 0
    critical_stock_count = 0
    
    for pp in packaged_products:
        # Get product name
        product = db.query(models.Product).filter(models.Product.id == pp.product_id).first()
        product_name = product.name if product else "Unknown Product"
        
        # Determine stock status
        status = "normal"
        if pp.current_stock <= pp.reorder_level:
            status = "low"
            low_stock_count += 1
        if pp.current_stock <= pp.min_stock_level:
            status = "critical"
            critical_stock_count += 1
        
        # Format packaging size
        size_display = pp.custom_size if pp.packaging_size == schemas_inventory.PackagingSize.CUSTOM else pp.packaging_size
        
        result_items.append({
            "id": pp.id,
            "product_id": pp.product_id,
            "product_name": product_name,
            "packaging_size": size_display,
            "weight_value": pp.weight_value,
            "weight_unit": pp.weight_unit,
            "current_stock": pp.current_stock,
            "min_stock_level": pp.min_stock_level,
            "reorder_level": pp.reorder_level,
            "status": status
        })
    
    return {
        "items": result_items,
        "low_stock_count": low_stock_count,
        "critical_stock_count": critical_stock_count
    }

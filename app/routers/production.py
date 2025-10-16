from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc, or_, and_
from typing import List, Optional, Dict, Any
from datetime import datetime, date
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

# Helper function to generate sequential numbers
def generate_sequential_number(db: Session, prefix: str, table, column_name: str) -> str:
    # Get the count of existing records
    count = db.query(func.count(getattr(table, "id"))).scalar()
    # Generate a sequential number with padding
    return f"{prefix}{(count + 1):06d}"

# Bill of Materials APIs
@router.post("/bom", response_model=schemas_inventory.BillOfMaterial, status_code=status.HTTP_201_CREATED)
async def create_bill_of_material(
    bom: schemas_inventory.BillOfMaterialCreate,
    current_user: schemas.User = Depends(get_admin_or_company_user),
    db: Session = Depends(get_db)
):
    # Check if product exists
    product = db.query(models.Product).filter(models.Product.id == bom.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Create bill of material
    db_bom = models_inventory.BillOfMaterial(
        product_id=bom.product_id,
        name=bom.name,
        description=bom.description,
        version=bom.version,
        is_active=bom.is_active,
        created_by=current_user.id
    )
    
    db.add(db_bom)
    db.commit()
    db.refresh(db_bom)
    
    # Add BOM items
    for item in bom.items:
        # Check if inventory item exists
        inventory_item = db.query(models_inventory.InventoryItem).filter(models_inventory.InventoryItem.id == item.inventory_item_id).first()
        if not inventory_item:
            raise HTTPException(status_code=404, detail=f"Inventory item with id {item.inventory_item_id} not found")
        
        db_item = models_inventory.BillOfMaterialItem(
            bom_id=db_bom.id,
            inventory_item_id=item.inventory_item_id,
            quantity=item.quantity,
            unit_of_measure=item.unit_of_measure,
            notes=item.notes
        )
        
        db.add(db_item)
    
    db.commit()
    db.refresh(db_bom)
    
    return db_bom

@router.get("/bom", response_model=List[schemas_inventory.BillOfMaterial])
async def read_bill_of_materials(
    skip: int = 0,
    limit: int = 100,
    product_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(models_inventory.BillOfMaterial)
    
    # Apply filters
    if product_id:
        query = query.filter(models_inventory.BillOfMaterial.product_id == product_id)
    
    if is_active is not None:
        query = query.filter(models_inventory.BillOfMaterial.is_active == is_active)
    
    # Order by created_at descending (newest first)
    query = query.order_by(desc(models_inventory.BillOfMaterial.created_at))
    
    boms = query.offset(skip).limit(limit).all()
    return boms

@router.get("/bom/{bom_id}", response_model=schemas_inventory.BillOfMaterial)
async def read_bill_of_material(
    bom_id: int,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    bom = db.query(models_inventory.BillOfMaterial).filter(models_inventory.BillOfMaterial.id == bom_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="Bill of material not found")
    return bom

@router.put("/bom/{bom_id}/activate", response_model=schemas_inventory.BillOfMaterial)
async def activate_bill_of_material(
    bom_id: int,
    current_user: schemas.User = Depends(get_admin_or_company_user),
    db: Session = Depends(get_db)
):
    db_bom = db.query(models_inventory.BillOfMaterial).filter(models_inventory.BillOfMaterial.id == bom_id).first()
    if not db_bom:
        raise HTTPException(status_code=404, detail="Bill of material not found")
    
    # Deactivate all other BOMs for this product
    other_boms = db.query(models_inventory.BillOfMaterial).filter(
        models_inventory.BillOfMaterial.product_id == db_bom.product_id,
        models_inventory.BillOfMaterial.id != bom_id
    ).all()
    
    for other_bom in other_boms:
        other_bom.is_active = False
    
    # Activate this BOM
    db_bom.is_active = True
    
    db.commit()
    db.refresh(db_bom)
    
    return db_bom

@router.put("/bom/{bom_id}/deactivate", response_model=schemas_inventory.BillOfMaterial)
async def deactivate_bill_of_material(
    bom_id: int,
    current_user: schemas.User = Depends(get_admin_or_company_user),
    db: Session = Depends(get_db)
):
    db_bom = db.query(models_inventory.BillOfMaterial).filter(models_inventory.BillOfMaterial.id == bom_id).first()
    if not db_bom:
        raise HTTPException(status_code=404, detail="Bill of material not found")
    
    # Deactivate this BOM
    db_bom.is_active = False
    
    db.commit()
    db.refresh(db_bom)
    
    return db_bom

@router.delete("/bom/{bom_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bill_of_material(
    bom_id: int,
    current_user: schemas.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    db_bom = db.query(models_inventory.BillOfMaterial).filter(models_inventory.BillOfMaterial.id == bom_id).first()
    if not db_bom:
        raise HTTPException(status_code=404, detail="Bill of material not found")
    
    # Check if BOM is used in any production batches
    production_batches = db.query(models_inventory.ProductionBatch).filter(models_inventory.ProductionBatch.bom_id == bom_id).first()
    if production_batches:
        raise HTTPException(status_code=400, detail="Cannot delete bill of material as it is used in production batches")
    
    # Delete BOM items first
    db.query(models_inventory.BillOfMaterialItem).filter(models_inventory.BillOfMaterialItem.bom_id == bom_id).delete()
    
    # Delete BOM
    db.delete(db_bom)
    db.commit()
    
    return

# Production Batch APIs
@router.post("/batches", response_model=schemas_inventory.ProductionBatch, status_code=status.HTTP_201_CREATED)
async def create_production_batch(
    batch: schemas_inventory.ProductionBatchCreate,
    current_user: schemas.User = Depends(get_admin_or_company_user),
    db: Session = Depends(get_db)
):
    # Check if product exists
    product = db.query(models.Product).filter(models.Product.id == batch.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if BOM exists
    bom = db.query(models_inventory.BillOfMaterial).filter(models_inventory.BillOfMaterial.id == batch.bom_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="Bill of material not found")
    
    # Check if BOM belongs to the product
    if bom.product_id != batch.product_id:
        raise HTTPException(status_code=400, detail="Bill of material does not belong to this product")
    
    # Generate batch number
    batch_number = generate_sequential_number(db, "BATCH", models_inventory.ProductionBatch, "batch_number")
    
    # Create production batch
    db_batch = models_inventory.ProductionBatch(
        batch_number=batch_number,
        product_id=batch.product_id,
        bom_id=batch.bom_id,
        planned_quantity=batch.planned_quantity,
        production_date=batch.production_date,
        status=batch.status,
        notes=batch.notes,
        created_by=current_user.id
    )
    
    db.add(db_batch)
    db.commit()
    db.refresh(db_batch)
    
    # Add packaged items
    for item in batch.packaged_items:
        # Check if packaged product exists
        packaged_product = db.query(models_inventory.PackagedProduct).filter(models_inventory.PackagedProduct.id == item.packaged_product_id).first()
        if not packaged_product:
            raise HTTPException(status_code=404, detail=f"Packaged product with id {item.packaged_product_id} not found")
        
        # Check if packaged product belongs to the product
        if packaged_product.product_id != batch.product_id:
            raise HTTPException(status_code=400, detail=f"Packaged product {item.packaged_product_id} does not belong to this product")
        
        db_item = models_inventory.ProductionBatchPackaging(
            batch_id=db_batch.id,
            packaged_product_id=item.packaged_product_id,
            quantity=item.quantity,
            notes=item.notes
        )
        
        db.add(db_item)
    
    db.commit()
    db.refresh(db_batch)
    
    return db_batch

@router.get("/batches", response_model=List[schemas_inventory.ProductionBatch])
async def read_production_batches(
    skip: int = 0,
    limit: int = 100,
    product_id: Optional[int] = None,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(models_inventory.ProductionBatch)
    
    # Apply filters
    if product_id:
        query = query.filter(models_inventory.ProductionBatch.product_id == product_id)
    
    if status:
        query = query.filter(models_inventory.ProductionBatch.status == status)
    
    if start_date:
        query = query.filter(models_inventory.ProductionBatch.production_date >= start_date)
    
    if end_date:
        query = query.filter(models_inventory.ProductionBatch.production_date <= end_date)
    
    # Order by production_date descending (newest first)
    query = query.order_by(desc(models_inventory.ProductionBatch.production_date))
    
    batches = query.offset(skip).limit(limit).all()
    return batches

@router.get("/batches/{batch_id}", response_model=schemas_inventory.ProductionBatch)
async def read_production_batch(
    batch_id: int,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    batch = db.query(models_inventory.ProductionBatch).filter(models_inventory.ProductionBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Production batch not found")
    return batch

@router.put("/batches/{batch_id}/start", response_model=schemas_inventory.ProductionBatch)
async def start_production_batch(
    batch_id: int,
    current_user: schemas.User = Depends(get_admin_or_company_user),
    db: Session = Depends(get_db)
):
    db_batch = db.query(models_inventory.ProductionBatch).filter(models_inventory.ProductionBatch.id == batch_id).first()
    if not db_batch:
        raise HTTPException(status_code=404, detail="Production batch not found")
    
    # Check if batch is in planned status
    if db_batch.status != "planned":
        raise HTTPException(status_code=400, detail="Only planned batches can be started")
    
    # Get BOM items
    bom_items = db.query(models_inventory.BillOfMaterialItem).filter(models_inventory.BillOfMaterialItem.bom_id == db_batch.bom_id).all()
    
    # Check if there's enough raw material for the batch
    for bom_item in bom_items:
        inventory_item = db.query(models_inventory.InventoryItem).filter(models_inventory.InventoryItem.id == bom_item.inventory_item_id).first()
        if not inventory_item:
            continue
        
        # Calculate required quantity
        required_qty = bom_item.quantity * db_batch.planned_quantity
        
        # Check if enough stock is available
        if inventory_item.current_stock < required_qty:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient stock for {inventory_item.name}. Required: {required_qty}, Available: {inventory_item.current_stock}"
            )
    
    # Consume raw materials
    for bom_item in bom_items:
        inventory_item = db.query(models_inventory.InventoryItem).filter(models_inventory.InventoryItem.id == bom_item.inventory_item_id).first()
        if not inventory_item:
            continue
        
        # Calculate required quantity
        required_qty = bom_item.quantity * db_batch.planned_quantity
        
        # Create stock movement
        stock_movement = models_inventory.StockMovement(
            inventory_item_id=bom_item.inventory_item_id,
            movement_type=schemas_inventory.StockMovementType.PRODUCTION,
            quantity=-required_qty,  # Negative quantity for consumption
            reference_number=db_batch.batch_number,
            reference_type="production_batch",
            reference_id=db_batch.id,
            notes=f"Production batch {db_batch.batch_number}",
            performed_by=current_user.id
        )
        db.add(stock_movement)
        
        # Update inventory item stock
        inventory_item.current_stock -= required_qty
    
    # Update batch status
    db_batch.status = "in_progress"
    
    db.commit()
    db.refresh(db_batch)
    
    return db_batch

@router.put("/batches/{batch_id}/complete", response_model=schemas_inventory.ProductionBatch)
async def complete_production_batch(
    batch_id: int,
    produced_quantity: int,
    current_user: schemas.User = Depends(get_admin_or_company_user),
    db: Session = Depends(get_db)
):
    db_batch = db.query(models_inventory.ProductionBatch).filter(models_inventory.ProductionBatch.id == batch_id).first()
    if not db_batch:
        raise HTTPException(status_code=404, detail="Production batch not found")
    
    # Check if batch is in progress
    if db_batch.status != "in_progress":
        raise HTTPException(status_code=400, detail="Only in-progress batches can be completed")
    
    # Check if produced quantity is valid
    if produced_quantity <= 0 or produced_quantity > db_batch.planned_quantity:
        raise HTTPException(status_code=400, detail=f"Produced quantity must be between 1 and {db_batch.planned_quantity}")
    
    # Update batch
    db_batch.produced_quantity = produced_quantity
    db_batch.status = "completed"
    
    # Get packaged items
    packaged_items = db.query(models_inventory.ProductionBatchPackaging).filter(models_inventory.ProductionBatchPackaging.batch_id == batch_id).all()
    
    # Update packaged product stock
    for item in packaged_items:
        packaged_product = db.query(models_inventory.PackagedProduct).filter(models_inventory.PackagedProduct.id == item.packaged_product_id).first()
        if not packaged_product:
            continue
        
        # Calculate produced quantity for this packaging
        item_produced_qty = (item.quantity * produced_quantity) // db_batch.planned_quantity
        
        # Create packaged product movement
        pp_movement = models_inventory.PackagedProductMovement(
            packaged_product_id=item.packaged_product_id,
            movement_type=schemas_inventory.StockMovementType.PRODUCTION,
            quantity=item_produced_qty,
            reference_number=db_batch.batch_number,
            reference_type="production_batch",
            reference_id=db_batch.id,
            notes=f"Production batch {db_batch.batch_number} completed",
            performed_by=current_user.id
        )
        db.add(pp_movement)
        
        # Update packaged product stock
        packaged_product.current_stock += item_produced_qty
    
    db.commit()
    db.refresh(db_batch)
    
    return db_batch

@router.put("/batches/{batch_id}/cancel", response_model=schemas_inventory.ProductionBatch)
async def cancel_production_batch(
    batch_id: int,
    notes: str,
    current_user: schemas.User = Depends(get_admin_or_company_user),
    db: Session = Depends(get_db)
):
    db_batch = db.query(models_inventory.ProductionBatch).filter(models_inventory.ProductionBatch.id == batch_id).first()
    if not db_batch:
        raise HTTPException(status_code=404, detail="Production batch not found")
    
    # Check if batch can be cancelled
    if db_batch.status == "completed":
        raise HTTPException(status_code=400, detail="Completed batches cannot be cancelled")
    
    # If batch is in progress, return raw materials
    if db_batch.status == "in_progress":
        # Get BOM items
        bom_items = db.query(models_inventory.BillOfMaterialItem).filter(models_inventory.BillOfMaterialItem.bom_id == db_batch.bom_id).all()
        
        # Return raw materials
        for bom_item in bom_items:
            inventory_item = db.query(models_inventory.InventoryItem).filter(models_inventory.InventoryItem.id == bom_item.inventory_item_id).first()
            if not inventory_item:
                continue
            
            # Calculate required quantity
            required_qty = bom_item.quantity * db_batch.planned_quantity
            
            # Create stock movement
            stock_movement = models_inventory.StockMovement(
                inventory_item_id=bom_item.inventory_item_id,
                movement_type=schemas_inventory.StockMovementType.ADJUSTMENT,
                quantity=required_qty,  # Positive quantity for return
                reference_number=db_batch.batch_number,
                reference_type="production_batch_cancelled",
                reference_id=db_batch.id,
                notes=f"Production batch {db_batch.batch_number} cancelled: {notes}",
                performed_by=current_user.id
            )
            db.add(stock_movement)
            
            # Update inventory item stock
            inventory_item.current_stock += required_qty
    
    # Update batch status
    db_batch.status = "cancelled"
    db_batch.notes = (db_batch.notes or "") + f"\nCancelled: {notes}"
    
    db.commit()
    db.refresh(db_batch)
    
    return db_batch

@router.get("/material-requirements", response_model=List[Dict])
async def get_material_requirements(
    product_id: int,
    quantity: int,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Check if product exists
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get active BOM for the product
    bom = db.query(models_inventory.BillOfMaterial).filter(
        models_inventory.BillOfMaterial.product_id == product_id,
        models_inventory.BillOfMaterial.is_active == True
    ).first()
    
    if not bom:
        raise HTTPException(status_code=404, detail="No active bill of material found for this product")
    
    # Get BOM items
    bom_items = db.query(models_inventory.BillOfMaterialItem).filter(models_inventory.BillOfMaterialItem.bom_id == bom.id).all()
    
    # Calculate material requirements
    requirements = []
    for bom_item in bom_items:
        inventory_item = db.query(models_inventory.InventoryItem).filter(models_inventory.InventoryItem.id == bom_item.inventory_item_id).first()
        if not inventory_item:
            continue
        
        # Calculate required quantity
        required_qty = float(bom_item.quantity * quantity)
        
        # Check if enough stock is available
        is_sufficient = inventory_item.current_stock >= required_qty
        
        requirements.append({
            "inventory_item_id": inventory_item.id,
            "name": inventory_item.name,
            "code": inventory_item.code,
            "unit_of_measure": bom_item.unit_of_measure,
            "required_quantity": required_qty,
            "available_quantity": float(inventory_item.current_stock),
            "is_sufficient": is_sufficient,
            "shortage": max(0, required_qty - float(inventory_item.current_stock)) if not is_sufficient else 0
        })
    
    return requirements

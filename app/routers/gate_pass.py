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

# Helper function to generate sequential numbers
def generate_sequential_number(db: Session, prefix: str, table, column_name: str) -> str:
    # Get the count of existing records
    count = db.query(func.count(getattr(table, "id"))).scalar()
    # Generate a sequential number with padding
    return f"{prefix}{(count + 1):06d}"

# Gate Pass APIs
@router.post("/", response_model=schemas_inventory.GatePass, status_code=status.HTTP_201_CREATED)
async def create_gate_pass(
    gate_pass: schemas_inventory.GatePassCreate,
    current_user: schemas.User = Depends(get_admin_or_company_user),
    db: Session = Depends(get_db)
):
    # Generate gate pass number
    pass_number = generate_sequential_number(db, "GP", models_inventory.GatePass, "pass_number")
    
    # Create gate pass
    db_gate_pass = models_inventory.GatePass(
        pass_number=pass_number,
        pass_type=gate_pass.pass_type,
        pass_date=gate_pass.pass_date,
        reference_number=gate_pass.reference_number,
        reference_type=gate_pass.reference_type,
        reference_id=gate_pass.reference_id,
        party_name=gate_pass.party_name,
        vehicle_number=gate_pass.vehicle_number,
        driver_name=gate_pass.driver_name,
        driver_contact=gate_pass.driver_contact,
        notes=gate_pass.notes,
        issued_by=current_user.id
    )
    
    db.add(db_gate_pass)
    db.commit()
    db.refresh(db_gate_pass)
    
    # Add gate pass items
    for item in gate_pass.items:
        # Validate item_id based on item_type
        if item.item_type == "raw_material":
            inventory_item = db.query(models_inventory.InventoryItem).filter(models_inventory.InventoryItem.id == item.item_id).first()
            if not inventory_item:
                raise HTTPException(status_code=404, detail=f"Inventory item with id {item.item_id} not found")
        elif item.item_type == "packaged_product":
            packaged_product = db.query(models_inventory.PackagedProduct).filter(models_inventory.PackagedProduct.id == item.item_id).first()
            if not packaged_product:
                raise HTTPException(status_code=404, detail=f"Packaged product with id {item.item_id} not found")
        else:
            raise HTTPException(status_code=400, detail=f"Invalid item_type: {item.item_type}")
        
        db_item = models_inventory.GatePassItem(
            gate_pass_id=db_gate_pass.id,
            item_type=item.item_type,
            item_id=item.item_id,
            quantity=item.quantity,
            unit_of_measure=item.unit_of_measure,
            description=item.description
        )
        
        db.add(db_item)
        
        # Update inventory based on gate pass type
        if gate_pass.pass_type == schemas_inventory.GatePassType.INWARD:
            # For inward gate pass, increase inventory
            if item.item_type == "raw_material":
                # Create stock movement for raw material
                stock_movement = models_inventory.StockMovement(
                    inventory_item_id=item.item_id,
                    movement_type=schemas_inventory.StockMovementType.PURCHASE,
                    quantity=item.quantity,
                    reference_number=pass_number,
                    reference_type="gate_pass",
                    reference_id=db_gate_pass.id,
                    notes=f"Inward gate pass {pass_number}",
                    performed_by=current_user.id
                )
                db.add(stock_movement)
                
                # Update inventory item stock
                inventory_item.current_stock += item.quantity
                
            elif item.item_type == "packaged_product":
                # Create packaged product movement
                pp_movement = models_inventory.PackagedProductMovement(
                    packaged_product_id=item.item_id,
                    movement_type=schemas_inventory.StockMovementType.PRODUCTION,
                    quantity=int(item.quantity),
                    reference_number=pass_number,
                    reference_type="gate_pass",
                    reference_id=db_gate_pass.id,
                    notes=f"Inward gate pass {pass_number}",
                    performed_by=current_user.id
                )
                db.add(pp_movement)
                
                # Update packaged product stock
                packaged_product.current_stock += int(item.quantity)
                
        elif gate_pass.pass_type == schemas_inventory.GatePassType.OUTWARD:
            # For outward gate pass, decrease inventory
            if item.item_type == "raw_material":
                # Check if sufficient stock is available
                if inventory_item.current_stock < item.quantity:
                    raise HTTPException(status_code=400, detail=f"Insufficient stock for inventory item {inventory_item.name}")
                
                # Create stock movement for raw material
                stock_movement = models_inventory.StockMovement(
                    inventory_item_id=item.item_id,
                    movement_type=schemas_inventory.StockMovementType.SALES,
                    quantity=-item.quantity,  # Negative quantity for outward
                    reference_number=pass_number,
                    reference_type="gate_pass",
                    reference_id=db_gate_pass.id,
                    notes=f"Outward gate pass {pass_number}",
                    performed_by=current_user.id
                )
                db.add(stock_movement)
                
                # Update inventory item stock
                inventory_item.current_stock -= item.quantity
                
            elif item.item_type == "packaged_product":
                # Check if sufficient stock is available
                if packaged_product.current_stock < int(item.quantity):
                    raise HTTPException(status_code=400, detail=f"Insufficient stock for packaged product {packaged_product.id}")
                
                # Create packaged product movement
                pp_movement = models_inventory.PackagedProductMovement(
                    packaged_product_id=item.item_id,
                    movement_type=schemas_inventory.StockMovementType.SALES,
                    quantity=int(item.quantity),
                    reference_number=pass_number,
                    reference_type="gate_pass",
                    reference_id=db_gate_pass.id,
                    notes=f"Outward gate pass {pass_number}",
                    performed_by=current_user.id
                )
                db.add(pp_movement)
                
                # Update packaged product stock
                packaged_product.current_stock -= int(item.quantity)
    
    db.commit()
    db.refresh(db_gate_pass)
    
    return db_gate_pass

@router.get("/", response_model=List[schemas_inventory.GatePass])
async def read_gate_passes(
    skip: int = 0,
    limit: int = 100,
    pass_type: Optional[schemas_inventory.GatePassType] = None,
    reference_type: Optional[str] = None,
    reference_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(models_inventory.GatePass)
    
    # Apply filters
    if pass_type:
        query = query.filter(models_inventory.GatePass.pass_type == pass_type)
    
    if reference_type:
        query = query.filter(models_inventory.GatePass.reference_type == reference_type)
    
    if reference_id:
        query = query.filter(models_inventory.GatePass.reference_id == reference_id)
    
    if start_date:
        query = query.filter(models_inventory.GatePass.pass_date >= start_date)
    
    if end_date:
        query = query.filter(models_inventory.GatePass.pass_date <= end_date)
    
    # Order by pass_date descending (newest first)
    query = query.order_by(desc(models_inventory.GatePass.pass_date))
    
    gate_passes = query.offset(skip).limit(limit).all()
    return gate_passes

@router.get("/{gate_pass_id}", response_model=schemas_inventory.GatePass)
async def read_gate_pass(
    gate_pass_id: int,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    gate_pass = db.query(models_inventory.GatePass).filter(models_inventory.GatePass.id == gate_pass_id).first()
    if not gate_pass:
        raise HTTPException(status_code=404, detail="Gate pass not found")
    return gate_pass

@router.put("/{gate_pass_id}/approve", response_model=schemas_inventory.GatePass)
async def approve_gate_pass(
    gate_pass_id: int,
    current_user: schemas.User = Depends(get_admin_or_company_user),
    db: Session = Depends(get_db)
):
    db_gate_pass = db.query(models_inventory.GatePass).filter(models_inventory.GatePass.id == gate_pass_id).first()
    if not db_gate_pass:
        raise HTTPException(status_code=404, detail="Gate pass not found")
    
    # Check if gate pass is already approved
    if db_gate_pass.approved_by:
        raise HTTPException(status_code=400, detail="Gate pass is already approved")
    
    # Update gate pass
    db_gate_pass.approved_by = current_user.id
    
    db.commit()
    db.refresh(db_gate_pass)
    
    return db_gate_pass

@router.get("/items/{gate_pass_id}", response_model=List[schemas_inventory.GatePassItem])
async def read_gate_pass_items(
    gate_pass_id: int,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Check if gate pass exists
    gate_pass = db.query(models_inventory.GatePass).filter(models_inventory.GatePass.id == gate_pass_id).first()
    if not gate_pass:
        raise HTTPException(status_code=404, detail="Gate pass not found")
    
    # Get gate pass items
    items = db.query(models_inventory.GatePassItem).filter(models_inventory.GatePassItem.gate_pass_id == gate_pass_id).all()
    return items

@router.get("/print/{gate_pass_id}", response_model=Dict)
async def print_gate_pass(
    gate_pass_id: int,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Check if gate pass exists
    gate_pass = db.query(models_inventory.GatePass).filter(models_inventory.GatePass.id == gate_pass_id).first()
    if not gate_pass:
        raise HTTPException(status_code=404, detail="Gate pass not found")
    
    # Get gate pass items
    items = db.query(models_inventory.GatePassItem).filter(models_inventory.GatePassItem.gate_pass_id == gate_pass_id).all()
    
    # Get issuer and approver details
    issuer = db.query(models.User).filter(models.User.id == gate_pass.issued_by).first()
    approver = None
    if gate_pass.approved_by:
        approver = db.query(models.User).filter(models.User.id == gate_pass.approved_by).first()
    
    # Format items with details
    formatted_items = []
    for item in items:
        item_details = {
            "id": item.id,
            "item_type": item.item_type,
            "item_id": item.item_id,
            "quantity": float(item.quantity),
            "unit_of_measure": item.unit_of_measure,
            "description": item.description
        }
        
        # Add item name based on type
        if item.item_type == "raw_material":
            inventory_item = db.query(models_inventory.InventoryItem).filter(models_inventory.InventoryItem.id == item.item_id).first()
            if inventory_item:
                item_details["name"] = inventory_item.name
                item_details["code"] = inventory_item.code
        elif item.item_type == "packaged_product":
            packaged_product = db.query(models_inventory.PackagedProduct).filter(models_inventory.PackagedProduct.id == item.item_id).first()
            if packaged_product:
                product = db.query(models.Product).filter(models.Product.id == packaged_product.product_id).first()
                if product:
                    item_details["name"] = product.name
                    item_details["code"] = product.sku
                    item_details["packaging_size"] = packaged_product.packaging_size
        
        formatted_items.append(item_details)
    
    # Prepare response
    result = {
        "gate_pass": {
            "id": gate_pass.id,
            "pass_number": gate_pass.pass_number,
            "pass_type": gate_pass.pass_type,
            "pass_date": gate_pass.pass_date,
            "reference_number": gate_pass.reference_number,
            "reference_type": gate_pass.reference_type,
            "reference_id": gate_pass.reference_id,
            "party_name": gate_pass.party_name,
            "vehicle_number": gate_pass.vehicle_number,
            "driver_name": gate_pass.driver_name,
            "driver_contact": gate_pass.driver_contact,
            "notes": gate_pass.notes,
            "created_at": gate_pass.created_at,
            "issuer": {
                "id": issuer.id,
                "name": issuer.full_name,
                "role": issuer.role
            } if issuer else None,
            "approver": {
                "id": approver.id,
                "name": approver.full_name,
                "role": approver.role
            } if approver else None
        },
        "items": formatted_items
    }
    
    return result

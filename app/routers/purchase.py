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

# Helper function to generate sequential numbers
def generate_sequential_number(db: Session, prefix: str, table, column_name: str) -> str:
    # Get the count of existing records
    count = db.query(func.count(getattr(table, "id"))).scalar()
    # Generate a sequential number with padding
    return f"{prefix}{(count + 1):06d}"

# Supplier APIs
@router.post("/suppliers", response_model=schemas_inventory.Supplier, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    supplier: schemas_inventory.SupplierCreate,
    current_user: schemas.User = Depends(get_admin_or_company_user),
    db: Session = Depends(get_db)
):
    # Check if code already exists
    existing_supplier = db.query(models_inventory.Supplier).filter(models_inventory.Supplier.code == supplier.code).first()
    if existing_supplier:
        raise HTTPException(status_code=400, detail="Supplier with this code already exists")
    
    # Create supplier
    db_supplier = models_inventory.Supplier(
        name=supplier.name,
        code=supplier.code,
        contact_person=supplier.contact_person,
        email=supplier.email,
        phone=supplier.phone,
        address=supplier.address,
        gst_number=supplier.gst_number,
        pan_number=supplier.pan_number,
        payment_terms=supplier.payment_terms,
        credit_limit=supplier.credit_limit,
        is_active=supplier.is_active,
        notes=supplier.notes
    )
    
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    
    return db_supplier

@router.get("/suppliers", response_model=List[schemas_inventory.Supplier])
async def read_suppliers(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(models_inventory.Supplier)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                models_inventory.Supplier.name.ilike(f"%{search}%"),
                models_inventory.Supplier.code.ilike(f"%{search}%"),
                models_inventory.Supplier.contact_person.ilike(f"%{search}%"),
                models_inventory.Supplier.email.ilike(f"%{search}%"),
                models_inventory.Supplier.phone.ilike(f"%{search}%")
            )
        )
    
    if is_active is not None:
        query = query.filter(models_inventory.Supplier.is_active == is_active)
    
    suppliers = query.offset(skip).limit(limit).all()
    return suppliers

@router.get("/suppliers/{supplier_id}", response_model=schemas_inventory.Supplier)
async def read_supplier(
    supplier_id: int,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    supplier = db.query(models_inventory.Supplier).filter(models_inventory.Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier

@router.put("/suppliers/{supplier_id}", response_model=schemas_inventory.Supplier)
async def update_supplier(
    supplier_id: int,
    supplier_update: schemas_inventory.SupplierUpdate,
    current_user: schemas.User = Depends(get_admin_or_company_user),
    db: Session = Depends(get_db)
):
    db_supplier = db.query(models_inventory.Supplier).filter(models_inventory.Supplier.id == supplier_id).first()
    if not db_supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Update fields if provided
    update_data = supplier_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_supplier, key, value)
    
    db.commit()
    db.refresh(db_supplier)
    
    return db_supplier

@router.delete("/suppliers/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_supplier(
    supplier_id: int,
    current_user: schemas.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    db_supplier = db.query(models_inventory.Supplier).filter(models_inventory.Supplier.id == supplier_id).first()
    if not db_supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Check if supplier has any purchase orders
    purchase_orders = db.query(models_inventory.PurchaseOrder).filter(models_inventory.PurchaseOrder.supplier_id == supplier_id).first()
    if purchase_orders:
        # Instead of deleting, mark as inactive
        db_supplier.is_active = False
        db.commit()
        return
    
    # Delete if not used anywhere
    db.delete(db_supplier)
    db.commit()
    
    return

# Purchase Indent APIs
@router.post("/indents", response_model=schemas_inventory.PurchaseIndent, status_code=status.HTTP_201_CREATED)
async def create_purchase_indent(
    indent: schemas_inventory.PurchaseIndentCreate,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Generate indent number
    indent_number = generate_sequential_number(db, "IND", models_inventory.PurchaseIndent, "indent_number")
    
    # Create purchase indent
    db_indent = models_inventory.PurchaseIndent(
        indent_number=indent_number,
        requested_by=current_user.id,
        department=indent.department,
        request_date=indent.request_date,
        required_by_date=indent.required_by_date,
        status=indent.status,
        notes=indent.notes
    )
    
    db.add(db_indent)
    db.commit()
    db.refresh(db_indent)
    
    # Add indent items
    for item in indent.items:
        # Check if inventory item exists
        inventory_item = db.query(models_inventory.InventoryItem).filter(models_inventory.InventoryItem.id == item.inventory_item_id).first()
        if not inventory_item:
            raise HTTPException(status_code=404, detail=f"Inventory item with id {item.inventory_item_id} not found")
        
        db_item = models_inventory.PurchaseIndentItem(
            indent_id=db_indent.id,
            inventory_item_id=item.inventory_item_id,
            quantity=item.quantity,
            unit_of_measure=item.unit_of_measure,
            estimated_price=item.estimated_price,
            notes=item.notes
        )
        
        db.add(db_item)
    
    db.commit()
    db.refresh(db_indent)
    
    return db_indent

@router.get("/indents", response_model=List[schemas_inventory.PurchaseIndent])
async def read_purchase_indents(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    requested_by: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(models_inventory.PurchaseIndent)
    
    # Apply filters
    if status:
        query = query.filter(models_inventory.PurchaseIndent.status == status)
    
    if requested_by:
        query = query.filter(models_inventory.PurchaseIndent.requested_by == requested_by)
    
    if start_date:
        query = query.filter(models_inventory.PurchaseIndent.request_date >= start_date)
    
    if end_date:
        query = query.filter(models_inventory.PurchaseIndent.request_date <= end_date)
    
    # Order by request_date descending (newest first)
    query = query.order_by(desc(models_inventory.PurchaseIndent.request_date))
    
    indents = query.offset(skip).limit(limit).all()
    return indents

@router.get("/indents/{indent_id}", response_model=schemas_inventory.PurchaseIndent)
async def read_purchase_indent(
    indent_id: int,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    indent = db.query(models_inventory.PurchaseIndent).filter(models_inventory.PurchaseIndent.id == indent_id).first()
    if not indent:
        raise HTTPException(status_code=404, detail="Purchase indent not found")
    return indent

@router.put("/indents/{indent_id}/approve", response_model=schemas_inventory.PurchaseIndent)
async def approve_purchase_indent(
    indent_id: int,
    current_user: schemas.User = Depends(get_admin_or_company_user),
    db: Session = Depends(get_db)
):
    db_indent = db.query(models_inventory.PurchaseIndent).filter(models_inventory.PurchaseIndent.id == indent_id).first()
    if not db_indent:
        raise HTTPException(status_code=404, detail="Purchase indent not found")
    
    # Check if indent is in pending status
    if db_indent.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending indents can be approved")
    
    # Update indent status
    db_indent.status = "approved"
    db_indent.approved_by = current_user.id
    db_indent.approved_at = datetime.now()
    
    db.commit()
    db.refresh(db_indent)
    
    return db_indent

@router.put("/indents/{indent_id}/reject", response_model=schemas_inventory.PurchaseIndent)
async def reject_purchase_indent(
    indent_id: int,
    notes: str,
    current_user: schemas.User = Depends(get_admin_or_company_user),
    db: Session = Depends(get_db)
):
    db_indent = db.query(models_inventory.PurchaseIndent).filter(models_inventory.PurchaseIndent.id == indent_id).first()
    if not db_indent:
        raise HTTPException(status_code=404, detail="Purchase indent not found")
    
    # Check if indent is in pending status
    if db_indent.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending indents can be rejected")
    
    # Update indent status
    db_indent.status = "rejected"
    db_indent.approved_by = current_user.id
    db_indent.approved_at = datetime.now()
    db_indent.notes = notes
    
    db.commit()
    db.refresh(db_indent)
    
    return db_indent

# Purchase Order APIs
@router.post("/orders", response_model=schemas_inventory.PurchaseOrder, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    order: schemas_inventory.PurchaseOrderCreate,
    current_user: schemas.User = Depends(get_admin_or_company_user),
    db: Session = Depends(get_db)
):
    # Check if supplier exists
    supplier = db.query(models_inventory.Supplier).filter(models_inventory.Supplier.id == order.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Check if indent exists if provided
    if order.indent_id:
        indent = db.query(models_inventory.PurchaseIndent).filter(models_inventory.PurchaseIndent.id == order.indent_id).first()
        if not indent:
            raise HTTPException(status_code=404, detail="Purchase indent not found")
        
        # Check if indent is approved
        if indent.status != "approved":
            raise HTTPException(status_code=400, detail="Purchase indent must be approved before creating a purchase order")
    
    # Generate PO number
    po_number = generate_sequential_number(db, "PO", models_inventory.PurchaseOrder, "po_number")
    
    # Calculate totals
    subtotal = 0.0
    tax_amount = 0.0
    discount_amount = 0.0
    
    for item in order.items:
        # Calculate item total
        item_subtotal = item.quantity * item.unit_price
        item_tax = item_subtotal * (item.tax_rate / 100)
        item_total = item_subtotal + item_tax - item.discount_amount
        
        subtotal += item_subtotal
        tax_amount += item_tax
        discount_amount += item.discount_amount
    
    # Calculate total amount
    total_amount = subtotal + tax_amount - discount_amount + (order.shipping_amount if hasattr(order, 'shipping_amount') else 0)
    
    # Create purchase order
    db_order = models_inventory.PurchaseOrder(
        po_number=po_number,
        supplier_id=order.supplier_id,
        indent_id=order.indent_id,
        order_date=order.order_date,
        expected_delivery_date=order.expected_delivery_date,
        delivery_address=order.delivery_address,
        status=order.status,
        subtotal=subtotal,
        tax_amount=tax_amount,
        shipping_amount=order.shipping_amount if hasattr(order, 'shipping_amount') else 0,
        discount_amount=discount_amount,
        total_amount=total_amount,
        payment_terms=order.payment_terms,
        notes=order.notes,
        created_by=current_user.id
    )
    
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    # Add order items
    for item in order.items:
        # Check if inventory item exists
        inventory_item = db.query(models_inventory.InventoryItem).filter(models_inventory.InventoryItem.id == item.inventory_item_id).first()
        if not inventory_item:
            raise HTTPException(status_code=404, detail=f"Inventory item with id {item.inventory_item_id} not found")
        
        # Calculate item totals
        item_subtotal = item.quantity * item.unit_price
        item_tax = item_subtotal * (item.tax_rate / 100)
        item_total = item_subtotal + item_tax - item.discount_amount
        
        # Find indent item if indent_id is provided
        indent_item_id = None
        if order.indent_id and item.indent_item_id:
            indent_item = db.query(models_inventory.PurchaseIndentItem).filter(
                models_inventory.PurchaseIndentItem.id == item.indent_item_id,
                models_inventory.PurchaseIndentItem.indent_id == order.indent_id
            ).first()
            if indent_item:
                indent_item_id = indent_item.id
        
        db_item = models_inventory.PurchaseOrderItem(
            po_id=db_order.id,
            inventory_item_id=item.inventory_item_id,
            indent_item_id=indent_item_id,
            quantity=item.quantity,
            unit_of_measure=item.unit_of_measure,
            unit_price=item.unit_price,
            tax_rate=item.tax_rate,
            tax_amount=item_tax,
            discount_amount=item.discount_amount,
            total_amount=item_total,
            hsn_code=item.hsn_code,
            notes=item.notes
        )
        
        db.add(db_item)
    
    db.commit()
    db.refresh(db_order)
    
    return db_order

@router.get("/orders", response_model=List[schemas_inventory.PurchaseOrder])
async def read_purchase_orders(
    skip: int = 0,
    limit: int = 100,
    status: Optional[schemas_inventory.PurchaseOrderStatus] = None,
    supplier_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(models_inventory.PurchaseOrder)
    
    # Apply filters
    if status:
        query = query.filter(models_inventory.PurchaseOrder.status == status)
    
    if supplier_id:
        query = query.filter(models_inventory.PurchaseOrder.supplier_id == supplier_id)
    
    if start_date:
        query = query.filter(models_inventory.PurchaseOrder.order_date >= start_date)
    
    if end_date:
        query = query.filter(models_inventory.PurchaseOrder.order_date <= end_date)
    
    # Order by order_date descending (newest first)
    query = query.order_by(desc(models_inventory.PurchaseOrder.order_date))
    
    orders = query.offset(skip).limit(limit).all()
    return orders

@router.get("/orders/{order_id}", response_model=schemas_inventory.PurchaseOrder)
async def read_purchase_order(
    order_id: int,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    order = db.query(models_inventory.PurchaseOrder).filter(models_inventory.PurchaseOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return order

@router.put("/orders/{order_id}/approve", response_model=schemas_inventory.PurchaseOrder)
async def approve_purchase_order(
    order_id: int,
    current_user: schemas.User = Depends(get_admin_or_company_user),
    db: Session = Depends(get_db)
):
    db_order = db.query(models_inventory.PurchaseOrder).filter(models_inventory.PurchaseOrder.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    # Check if order is in draft or pending status
    if db_order.status not in [schemas_inventory.PurchaseOrderStatus.DRAFT, schemas_inventory.PurchaseOrderStatus.PENDING]:
        raise HTTPException(status_code=400, detail="Only draft or pending orders can be approved")
    
    # Update order status
    db_order.status = schemas_inventory.PurchaseOrderStatus.APPROVED
    db_order.approved_by = current_user.id
    db_order.approved_at = datetime.now()
    
    db.commit()
    db.refresh(db_order)
    
    return db_order

@router.put("/orders/{order_id}/cancel", response_model=schemas_inventory.PurchaseOrder)
async def cancel_purchase_order(
    order_id: int,
    notes: str,
    current_user: schemas.User = Depends(get_admin_or_company_user),
    db: Session = Depends(get_db)
):
    db_order = db.query(models_inventory.PurchaseOrder).filter(models_inventory.PurchaseOrder.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    # Check if order can be cancelled
    if db_order.status in [schemas_inventory.PurchaseOrderStatus.PARTIALLY_RECEIVED, schemas_inventory.PurchaseOrderStatus.RECEIVED]:
        raise HTTPException(status_code=400, detail="Cannot cancel orders that have been received")
    
    # Update order status
    db_order.status = schemas_inventory.PurchaseOrderStatus.CANCELLED
    db_order.notes = (db_order.notes or "") + f"\nCancelled on {datetime.now()}: {notes}"
    
    db.commit()
    db.refresh(db_order)
    
    return db_order

# Purchase Receipt APIs
@router.post("/receipts", response_model=schemas_inventory.PurchaseReceipt, status_code=status.HTTP_201_CREATED)
async def create_purchase_receipt(
    receipt: schemas_inventory.PurchaseReceiptCreate,
    current_user: schemas.User = Depends(get_admin_or_company_user),
    db: Session = Depends(get_db)
):
    # Check if purchase order exists
    po = db.query(models_inventory.PurchaseOrder).filter(models_inventory.PurchaseOrder.id == receipt.po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    # Check if purchase order is approved
    if po.status != schemas_inventory.PurchaseOrderStatus.APPROVED and po.status != schemas_inventory.PurchaseOrderStatus.PARTIALLY_RECEIVED:
        raise HTTPException(status_code=400, detail="Purchase order must be approved before receiving")
    
    # Generate receipt number
    receipt_number = generate_sequential_number(db, "GRN", models_inventory.PurchaseReceipt, "receipt_number")
    
    # Create purchase receipt
    db_receipt = models_inventory.PurchaseReceipt(
        receipt_number=receipt_number,
        po_id=receipt.po_id,
        receipt_date=receipt.receipt_date,
        supplier_invoice_number=receipt.supplier_invoice_number,
        supplier_invoice_date=receipt.supplier_invoice_date,
        notes=receipt.notes,
        received_by=current_user.id
    )
    
    db.add(db_receipt)
    db.commit()
    db.refresh(db_receipt)
    
    # Add receipt items and create stock movements
    all_items_fully_received = True
    
    for item in receipt.items:
        # Check if PO item exists
        po_item = db.query(models_inventory.PurchaseOrderItem).filter(
            models_inventory.PurchaseOrderItem.id == item.po_item_id,
            models_inventory.PurchaseOrderItem.po_id == receipt.po_id
        ).first()
        
        if not po_item:
            raise HTTPException(status_code=404, detail=f"Purchase order item with id {item.po_item_id} not found")
        
        # Check if quantity is valid
        remaining_qty = po_item.quantity - po_item.received_quantity
        if item.received_quantity > remaining_qty:
            raise HTTPException(status_code=400, detail=f"Received quantity exceeds remaining quantity for item {po_item.id}")
        
        # Create receipt item
        db_receipt_item = models_inventory.PurchaseReceiptItem(
            receipt_id=db_receipt.id,
            po_item_id=item.po_item_id,
            received_quantity=item.received_quantity,
            accepted_quantity=item.accepted_quantity,
            rejected_quantity=item.rejected_quantity,
            rejection_reason=item.rejection_reason,
            batch_number=item.batch_number,
            expiry_date=item.expiry_date,
            notes=item.notes
        )
        
        db.add(db_receipt_item)
        
        # Update PO item received quantity
        po_item.received_quantity += item.received_quantity
        
        # Check if all items are fully received
        if po_item.received_quantity < po_item.quantity:
            all_items_fully_received = False
        
        # Create stock movement for accepted quantity
        if item.accepted_quantity > 0:
            stock_movement = models_inventory.StockMovement(
                inventory_item_id=po_item.inventory_item_id,
                movement_type=schemas_inventory.StockMovementType.PURCHASE,
                quantity=item.accepted_quantity,
                unit_price=po_item.unit_price,
                total_value=po_item.unit_price * item.accepted_quantity,
                reference_number=po.po_number,
                reference_type="purchase_order",
                reference_id=po.id,
                notes=f"Received via GRN {receipt_number}",
                performed_by=current_user.id,
                purchase_receipt=db_receipt
            )
            
            db.add(stock_movement)
            
            # Update inventory item stock
            inventory_item = db.query(models_inventory.InventoryItem).filter(models_inventory.InventoryItem.id == po_item.inventory_item_id).first()
            if inventory_item:
                inventory_item.current_stock += Decimal(str(item.accepted_quantity))
    
    # Update purchase order status
    if all_items_fully_received:
        po.status = schemas_inventory.PurchaseOrderStatus.RECEIVED
    else:
        po.status = schemas_inventory.PurchaseOrderStatus.PARTIALLY_RECEIVED
    
    db.commit()
    db.refresh(db_receipt)
    
    return db_receipt

@router.get("/receipts", response_model=List[schemas_inventory.PurchaseReceipt])
async def read_purchase_receipts(
    skip: int = 0,
    limit: int = 100,
    po_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(models_inventory.PurchaseReceipt)
    
    # Apply filters
    if po_id:
        query = query.filter(models_inventory.PurchaseReceipt.po_id == po_id)
    
    if start_date:
        query = query.filter(models_inventory.PurchaseReceipt.receipt_date >= start_date)
    
    if end_date:
        query = query.filter(models_inventory.PurchaseReceipt.receipt_date <= end_date)
    
    # Order by receipt_date descending (newest first)
    query = query.order_by(desc(models_inventory.PurchaseReceipt.receipt_date))
    
    receipts = query.offset(skip).limit(limit).all()
    return receipts

@router.get("/receipts/{receipt_id}", response_model=schemas_inventory.PurchaseReceipt)
async def read_purchase_receipt(
    receipt_id: int,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    receipt = db.query(models_inventory.PurchaseReceipt).filter(models_inventory.PurchaseReceipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Purchase receipt not found")
    return receipt

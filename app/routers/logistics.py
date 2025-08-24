from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from ..database import get_db
from ..models_logistics import LogisticsProvider, Shipment, ShipmentTracking, DeliveryAttempt
from ..models_logistics import LogisticsProviderStatus, ShipmentStatus, DeliveryAttemptStatus
from ..models import Order, OrderStatus, User, UserRole
from ..schemas_logistics import (
    LogisticsProviderCreate, LogisticsProviderUpdate, LogisticsProvider,
    ShipmentCreate, ShipmentUpdate, ShipmentInDB, ShipmentComplete, ShipmentFilter,
    ShipmentTrackingCreate, ShipmentTracking,
    DeliveryAttemptCreate, DeliveryAttempt
)
from .auth import get_current_active_user, get_admin_user, get_seller_or_admin_user

router = APIRouter(
    prefix="/logistics",
    tags=["logistics"],
    responses={404: {"description": "Not found"}},
)

# Logistics Provider endpoints
@router.post("/providers", response_model=LogisticsProvider)
async def create_logistics_provider(
    provider: LogisticsProviderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Create a new logistics provider (Admin only)"""
    db_provider = LogisticsProvider(**provider.dict())
    db.add(db_provider)
    db.commit()
    db.refresh(db_provider)
    return db_provider

@router.get("/providers", response_model=List[LogisticsProvider])
async def get_logistics_providers(
    status: Optional[LogisticsProviderStatus] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all logistics providers with optional status filter"""
    query = db.query(LogisticsProvider)
    if status:
        query = query.filter(LogisticsProvider.status == status)
    return query.offset(skip).limit(limit).all()

@router.get("/providers/{provider_id}", response_model=LogisticsProvider)
async def get_logistics_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific logistics provider by ID"""
    provider = db.query(LogisticsProvider).filter(LogisticsProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Logistics provider not found")
    return provider

@router.put("/providers/{provider_id}", response_model=LogisticsProvider)
async def update_logistics_provider(
    provider_id: int,
    provider_update: LogisticsProviderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Update a logistics provider (Admin only)"""
    db_provider = db.query(LogisticsProvider).filter(LogisticsProvider.id == provider_id).first()
    if not db_provider:
        raise HTTPException(status_code=404, detail="Logistics provider not found")
    
    update_data = provider_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_provider, key, value)
    
    db.commit()
    db.refresh(db_provider)
    return db_provider

@router.delete("/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_logistics_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Delete a logistics provider (Admin only)"""
    db_provider = db.query(LogisticsProvider).filter(LogisticsProvider.id == provider_id).first()
    if not db_provider:
        raise HTTPException(status_code=404, detail="Logistics provider not found")
    
    # Check if provider has associated shipments
    shipment_count = db.query(Shipment).filter(Shipment.logistics_provider_id == provider_id).count()
    if shipment_count > 0:
        # Instead of deleting, mark as inactive
        db_provider.status = LogisticsProviderStatus.INACTIVE
        db.commit()
        return {"detail": "Provider has associated shipments. Marked as inactive instead of deleting."}
    else:
        db.delete(db_provider)
        db.commit()
        return {"detail": "Logistics provider deleted"}

# Shipment endpoints
@router.post("/shipments", response_model=ShipmentInDB)
async def create_shipment(
    shipment: ShipmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_seller_or_admin_user)
):
    """Create a new shipment for an order"""
    # Check if order exists and belongs to the seller
    order = db.query(Order).filter(Order.id == shipment.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if user is admin or the seller of the order
    if current_user.role != UserRole.ADMIN and order.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to create shipment for this order")
    
    # Check if logistics provider exists and is active
    provider = db.query(LogisticsProvider).filter(
        LogisticsProvider.id == shipment.logistics_provider_id,
        LogisticsProvider.status == LogisticsProviderStatus.ACTIVE
    ).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Logistics provider not found or inactive")
    
    # Generate tracking number if not provided
    if not shipment.tracking_number:
        shipment_dict = shipment.dict()
        tracking_prefix = provider.code[:3].upper()
        tracking_suffix = uuid.uuid4().hex[:8].upper()
        shipment_dict["tracking_number"] = f"{tracking_prefix}{datetime.now().strftime('%Y%m%d')}{tracking_suffix}"
        db_shipment = Shipment(**shipment_dict)
    else:
        db_shipment = Shipment(**shipment.dict())
    
    # Update order status to processing if it's pending
    if order.status == OrderStatus.PENDING:
        order.status = OrderStatus.PROCESSING
    
    db.add(db_shipment)
    db.commit()
    db.refresh(db_shipment)
    
    # Create initial tracking entry
    tracking_entry = ShipmentTracking(
        shipment_id=db_shipment.id,
        status=ShipmentStatus.PENDING,
        description="Shipment created and pending processing",
        timestamp=datetime.now()
    )
    db.add(tracking_entry)
    db.commit()
    
    return db_shipment

@router.get("/shipments", response_model=List[ShipmentInDB])
async def get_shipments(
    filter_params: ShipmentFilter = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get shipments with filtering options"""
    query = db.query(Shipment)
    
    # Apply filters
    if filter_params.order_id:
        query = query.filter(Shipment.order_id == filter_params.order_id)
    
    if filter_params.logistics_provider_id:
        query = query.filter(Shipment.logistics_provider_id == filter_params.logistics_provider_id)
    
    if filter_params.status:
        query = query.filter(Shipment.status == filter_params.status)
    
    if filter_params.tracking_number:
        query = query.filter(Shipment.tracking_number == filter_params.tracking_number)
    
    if filter_params.waybill_number:
        query = query.filter(Shipment.waybill_number == filter_params.waybill_number)
    
    if filter_params.start_date:
        query = query.filter(Shipment.created_at >= filter_params.start_date)
    
    if filter_params.end_date:
        query = query.filter(Shipment.created_at <= filter_params.end_date)
    
    # Apply sorting
    if filter_params.sort_by:
        if hasattr(Shipment, filter_params.sort_by):
            sort_column = getattr(Shipment, filter_params.sort_by)
            if filter_params.sort_desc:
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
    else:
        # Default sort by created_at desc
        query = query.order_by(desc(Shipment.created_at))
    
    # Apply pagination
    skip = (filter_params.page - 1) * filter_params.limit
    query = query.offset(skip).limit(filter_params.limit)
    
    return query.all()

@router.get("/shipments/{shipment_id}", response_model=ShipmentComplete)
async def get_shipment(
    shipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific shipment with all related data"""
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    # Check if user is admin, seller of the order, or buyer of the order
    order = db.query(Order).filter(Order.id == shipment.order_id).first()
    if (current_user.role != UserRole.ADMIN and 
        order.seller_id != current_user.id and 
        order.user_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this shipment")
    
    return shipment

@router.put("/shipments/{shipment_id}", response_model=ShipmentInDB)
async def update_shipment(
    shipment_id: int,
    shipment_update: ShipmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_seller_or_admin_user)
):
    """Update a shipment"""
    db_shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not db_shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    # Check if user is admin or the seller of the order
    order = db.query(Order).filter(Order.id == db_shipment.order_id).first()
    if current_user.role != UserRole.ADMIN and order.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this shipment")
    
    # Check if status is being updated
    old_status = db_shipment.status
    
    # Update shipment fields
    update_data = shipment_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_shipment, key, value)
    
    # If status changed, create a tracking update
    if 'status' in update_data and old_status != update_data['status']:
        tracking_entry = ShipmentTracking(
            shipment_id=db_shipment.id,
            status=update_data['status'],
            description=f"Status updated from {old_status} to {update_data['status']}",
            timestamp=datetime.now()
        )
        db.add(tracking_entry)
        
        # If delivered, update actual delivery date and order status
        if update_data['status'] == ShipmentStatus.DELIVERED and not db_shipment.actual_delivery_date:
            db_shipment.actual_delivery_date = datetime.now()
            order.status = OrderStatus.DELIVERED
    
    db.commit()
    db.refresh(db_shipment)
    return db_shipment

@router.delete("/shipments/{shipment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shipment(
    shipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Delete a shipment (Admin only)"""
    db_shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not db_shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    # Delete related tracking updates and delivery attempts
    db.query(ShipmentTracking).filter(ShipmentTracking.shipment_id == shipment_id).delete()
    db.query(DeliveryAttempt).filter(DeliveryAttempt.shipment_id == shipment_id).delete()
    
    db.delete(db_shipment)
    db.commit()
    return {"detail": "Shipment and related data deleted"}

# Shipment Tracking endpoints
@router.post("/tracking", response_model=ShipmentTracking)
async def add_tracking_update(
    tracking: ShipmentTrackingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_seller_or_admin_user)
):
    """Add a tracking update to a shipment"""
    # Check if shipment exists
    shipment = db.query(Shipment).filter(Shipment.id == tracking.shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    # Check if user is admin or the seller of the order
    order = db.query(Order).filter(Order.id == shipment.order_id).first()
    if current_user.role != UserRole.ADMIN and order.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update tracking for this shipment")
    
    # Create tracking update
    db_tracking = ShipmentTracking(**tracking.dict())
    db.add(db_tracking)
    
    # Update shipment status
    shipment.status = tracking.status
    
    # If delivered, update actual delivery date and order status
    if tracking.status == ShipmentStatus.DELIVERED and not shipment.actual_delivery_date:
        shipment.actual_delivery_date = tracking.timestamp
        order.status = OrderStatus.DELIVERED
    
    db.commit()
    db.refresh(db_tracking)
    return db_tracking

@router.get("/tracking/{shipment_id}", response_model=List[ShipmentTracking])
async def get_tracking_updates(
    shipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all tracking updates for a shipment"""
    # Check if shipment exists
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    # Get tracking updates ordered by timestamp
    tracking_updates = db.query(ShipmentTracking).filter(
        ShipmentTracking.shipment_id == shipment_id
    ).order_by(ShipmentTracking.timestamp.desc()).all()
    
    return tracking_updates

# Delivery Attempt endpoints
@router.post("/delivery-attempts", response_model=DeliveryAttempt)
async def add_delivery_attempt(
    attempt: DeliveryAttemptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_seller_or_admin_user)
):
    """Record a delivery attempt for a shipment"""
    # Check if shipment exists
    shipment = db.query(Shipment).filter(Shipment.id == attempt.shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    # Check if user is admin or the seller of the order
    order = db.query(Order).filter(Order.id == shipment.order_id).first()
    if current_user.role != UserRole.ADMIN and order.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to add delivery attempt for this shipment")
    
    # Create delivery attempt
    db_attempt = DeliveryAttempt(**attempt.dict())
    db.add(db_attempt)
    
    # Update shipment status based on attempt status
    if attempt.status == DeliveryAttemptStatus.SUCCESSFUL:
        shipment.status = ShipmentStatus.DELIVERED
        shipment.actual_delivery_date = attempt.timestamp
        order.status = OrderStatus.DELIVERED
        
        # Create tracking update for successful delivery
        tracking_entry = ShipmentTracking(
            shipment_id=shipment.id,
            status=ShipmentStatus.DELIVERED,
            description="Package delivered successfully",
            timestamp=attempt.timestamp
        )
        db.add(tracking_entry)
    
    elif attempt.status == DeliveryAttemptStatus.FAILED:
        shipment.status = ShipmentStatus.FAILED
        
        # Create tracking update for failed delivery
        tracking_entry = ShipmentTracking(
            shipment_id=shipment.id,
            status=ShipmentStatus.FAILED,
            description=f"Delivery attempt failed: {attempt.notes}",
            timestamp=attempt.timestamp
        )
        db.add(tracking_entry)
    
    db.commit()
    db.refresh(db_attempt)
    return db_attempt

@router.get("/delivery-attempts/{shipment_id}", response_model=List[DeliveryAttempt])
async def get_delivery_attempts(
    shipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all delivery attempts for a shipment"""
    # Check if shipment exists
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    # Get delivery attempts ordered by timestamp
    delivery_attempts = db.query(DeliveryAttempt).filter(
        DeliveryAttempt.shipment_id == shipment_id
    ).order_by(DeliveryAttempt.timestamp.desc()).all()
    
    return delivery_attempts

# Tracking by tracking number (public endpoint)
@router.get("/track/{tracking_number}", response_model=ShipmentComplete)
async def track_shipment(
    tracking_number: str,
    db: Session = Depends(get_db)
):
    """Public endpoint to track a shipment by tracking number"""
    shipment = db.query(Shipment).filter(Shipment.tracking_number == tracking_number).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    return shipment

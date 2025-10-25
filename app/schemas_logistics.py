from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

# Enums
class LogisticsProviderStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class ShipmentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETURNED = "returned"
    CANCELLED = "cancelled"

class DeliveryAttemptStatus(str, Enum):
    SCHEDULED = "scheduled"
    ATTEMPTED = "attempted"
    SUCCESSFUL = "successful"
    FAILED = "failed"
    RESCHEDULED = "rescheduled"

# Logistics Provider schemas
class LogisticsProviderBase(BaseModel):
    name: str
    code: str
    contact_email: EmailStr
    contact_phone: str
    website: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    api_endpoint: Optional[str] = None
    status: LogisticsProviderStatus = LogisticsProviderStatus.ACTIVE
    service_areas: Optional[List[str]] = None
    service_types: Optional[List[str]] = None
    pricing_tiers: Optional[Dict[str, Any]] = None

class LogisticsProviderCreate(LogisticsProviderBase):
    pass

class LogisticsProviderUpdate(BaseModel):
    name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    api_endpoint: Optional[str] = None
    status: Optional[LogisticsProviderStatus] = None
    service_areas: Optional[List[str]] = None
    service_types: Optional[List[str]] = None
    pricing_tiers: Optional[Dict[str, Any]] = None

class LogisticsProviderInDB(LogisticsProviderBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class LogisticsProvider(LogisticsProviderInDB):
    pass

# Shipment schemas
class ShipmentDimensions(BaseModel):
    length: float
    width: float
    height: float
    unit: str = "cm"

class Address(BaseModel):
    street: str
    city: str
    state: str
    postal_code: str
    country: str
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None

class ShipmentBase(BaseModel):
    order_id: int
    logistics_provider_id: int
    tracking_number: Optional[str] = None
    waybill_number: Optional[str] = None
    status: ShipmentStatus = ShipmentStatus.PENDING
    estimated_delivery_date: Optional[datetime] = None
    shipping_cost: float = 0.0
    weight: Optional[float] = None
    dimensions: Optional[ShipmentDimensions] = None
    pickup_address: Address
    delivery_address: Address
    special_instructions: Optional[str] = None
    signature_required: bool = False
    is_insured: bool = False
    insurance_amount: float = 0.0

class ShipmentCreate(ShipmentBase):
    pass

class ShipmentUpdate(BaseModel):
    logistics_provider_id: Optional[int] = None
    tracking_number: Optional[str] = None
    waybill_number: Optional[str] = None
    status: Optional[ShipmentStatus] = None
    estimated_delivery_date: Optional[datetime] = None
    actual_delivery_date: Optional[datetime] = None
    shipping_cost: Optional[float] = None
    weight: Optional[float] = None
    dimensions: Optional[ShipmentDimensions] = None
    pickup_address: Optional[Address] = None
    delivery_address: Optional[Address] = None
    special_instructions: Optional[str] = None
    signature_required: Optional[bool] = None
    is_insured: Optional[bool] = None
    insurance_amount: Optional[float] = None

class ShipmentInDB(ShipmentBase):
    id: int
    actual_delivery_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Shipment Tracking schemas
class ShipmentTrackingBase(BaseModel):
    shipment_id: int
    status: ShipmentStatus
    location: Optional[str] = None
    description: Optional[str] = None
    timestamp: datetime

class ShipmentTrackingCreate(ShipmentTrackingBase):
    pass

class ShipmentTrackingInDB(ShipmentTrackingBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ShipmentTracking(ShipmentTrackingInDB):
    pass

# Delivery Attempt schemas
class DeliveryAttemptBase(BaseModel):
    shipment_id: int
    attempt_number: int = 1
    status: DeliveryAttemptStatus
    timestamp: datetime
    notes: Optional[str] = None
    delivery_person: Optional[str] = None
    contact_made: bool = False
    signature_image_url: Optional[str] = None
    proof_of_delivery_url: Optional[str] = None

class DeliveryAttemptCreate(DeliveryAttemptBase):
    pass

class DeliveryAttemptInDB(DeliveryAttemptBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class DeliveryAttempt(DeliveryAttemptInDB):
    pass

# Complete Shipment with related data
class ShipmentComplete(ShipmentInDB):
    logistics_provider: LogisticsProvider
    tracking_updates: List[ShipmentTracking] = []
    delivery_attempts: List[DeliveryAttempt] = []

# Shipment Filter
class ShipmentFilter(BaseModel):
    order_id: Optional[int] = None
    logistics_provider_id: Optional[int] = None
    status: Optional[ShipmentStatus] = None
    tracking_number: Optional[str] = None
    waybill_number: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = 1
    limit: int = 10
    sort_by: Optional[str] = None
    sort_desc: bool = False

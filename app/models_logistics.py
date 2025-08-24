from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, Float, DateTime, Enum, Table, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from datetime import datetime

from .database import Base
from .models import OrderStatus, User, Order

# Logistics provider status enum
class LogisticsProviderStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

# Shipment status enum
class ShipmentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETURNED = "returned"
    CANCELLED = "cancelled"

# Delivery attempt status enum
class DeliveryAttemptStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    ATTEMPTED = "attempted"
    SUCCESSFUL = "successful"
    FAILED = "failed"
    RESCHEDULED = "rescheduled"

class LogisticsProvider(Base):
    __tablename__ = "logistics_providers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    code = Column(String, unique=True, index=True)
    contact_email = Column(String)
    contact_phone = Column(String)
    website = Column(String, nullable=True)
    api_key = Column(String, nullable=True)  # For integration with provider's API
    api_secret = Column(String, nullable=True)
    api_endpoint = Column(String, nullable=True)
    status = Column(Enum(LogisticsProviderStatus), default=LogisticsProviderStatus.ACTIVE)
    service_areas = Column(JSON, nullable=True)  # JSON array of regions/states covered
    service_types = Column(JSON, nullable=True)  # JSON array of service types (express, standard, etc.)
    pricing_tiers = Column(JSON, nullable=True)  # JSON object with pricing details
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    shipments = relationship("Shipment", back_populates="logistics_provider")

class Shipment(Base):
    __tablename__ = "shipments"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    logistics_provider_id = Column(Integer, ForeignKey("logistics_providers.id"))
    tracking_number = Column(String, unique=True, index=True)
    waybill_number = Column(String, nullable=True)
    status = Column(Enum(ShipmentStatus), default=ShipmentStatus.PENDING)
    estimated_delivery_date = Column(DateTime(timezone=True), nullable=True)
    actual_delivery_date = Column(DateTime(timezone=True), nullable=True)
    shipping_cost = Column(Float, default=0.0)
    weight = Column(Float, nullable=True)  # Weight in kg
    dimensions = Column(JSON, nullable=True)  # JSON with length, width, height
    pickup_address = Column(JSON)  # JSON with address details
    delivery_address = Column(JSON)  # JSON with address details
    special_instructions = Column(Text, nullable=True)
    signature_required = Column(Boolean, default=False)
    is_insured = Column(Boolean, default=False)
    insurance_amount = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    order = relationship("Order", back_populates="shipments")
    logistics_provider = relationship("LogisticsProvider", back_populates="shipments")
    tracking_updates = relationship("ShipmentTracking", back_populates="shipment")
    delivery_attempts = relationship("DeliveryAttempt", back_populates="shipment")

class ShipmentTracking(Base):
    __tablename__ = "shipment_tracking"
    
    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"))
    status = Column(Enum(ShipmentStatus))
    location = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    shipment = relationship("Shipment", back_populates="tracking_updates")

class DeliveryAttempt(Base):
    __tablename__ = "delivery_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"))
    attempt_number = Column(Integer, default=1)
    status = Column(Enum(DeliveryAttemptStatus))
    timestamp = Column(DateTime(timezone=True))
    notes = Column(Text, nullable=True)
    delivery_person = Column(String, nullable=True)
    contact_made = Column(Boolean, default=False)
    signature_image_url = Column(String, nullable=True)
    proof_of_delivery_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    shipment = relationship("Shipment", back_populates="delivery_attempts")

# Add relationship to Order model
Order.shipments = relationship("Shipment", back_populates="order")

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, Float, DateTime, Enum, Table, JSON, Date, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from datetime import datetime, date

from .database import Base
from . import models

# Inventory related enums
class UnitOfMeasure(str, enum.Enum):
    GRAM = "gram"
    KILOGRAM = "kilogram"
    LITER = "liter"
    MILLILITER = "milliliter"
    PIECE = "piece"
    BOX = "box"
    PACKET = "packet"
    CARTON = "carton"

class StockMovementType(str, enum.Enum):
    PURCHASE = "purchase"
    PRODUCTION = "production"
    SALES = "sales"
    RETURN = "return"
    ADJUSTMENT = "adjustment"
    TRANSFER = "transfer"
    WASTAGE = "wastage"

class PurchaseOrderStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    CANCELLED = "cancelled"

class GatePassType(str, enum.Enum):
    INWARD = "inward"
    OUTWARD = "outward"
    RETURN = "return"

class PackagingSize(str, enum.Enum):
    SIZE_50G = "50g"
    SIZE_100G = "100g"
    SIZE_500G = "500g"
    SIZE_1KG = "1kg"
    CUSTOM = "custom"

# Raw Material / Inventory Item
class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    code = Column(String, unique=True, index=True)
    description = Column(Text, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    unit_of_measure = Column(Enum(UnitOfMeasure))
    current_stock = Column(Numeric(precision=10, scale=3), default=0)  # Precise decimal for inventory
    min_stock_level = Column(Numeric(precision=10, scale=3), default=0)
    max_stock_level = Column(Numeric(precision=10, scale=3), nullable=True)
    reorder_level = Column(Numeric(precision=10, scale=3), default=0)
    cost_price = Column(Float, default=0.0)
    hsn_code = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_raw_material = Column(Boolean, default=True)  # True for raw materials, False for finished goods
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    category = relationship("models.Category")
    creator = relationship("models.User", foreign_keys=[created_by])
    stock_movements = relationship("StockMovement", back_populates="inventory_item")
    purchase_order_items = relationship("PurchaseOrderItem", back_populates="inventory_item")
    bom_items = relationship("BillOfMaterialItem", back_populates="inventory_item")

# Packaged Product (links to Product model and tracks packaging sizes)
class PackagedProduct(Base):
    __tablename__ = "packaged_products"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    packaging_size = Column(Enum(PackagingSize))
    custom_size = Column(String, nullable=True)  # For custom sizes not in enum
    weight_value = Column(Float)  # Numeric value of the weight
    weight_unit = Column(String)  # Unit of the weight (g, kg, etc.)
    items_per_package = Column(Integer, default=1)
    barcode = Column(String, nullable=True)
    current_stock = Column(Integer, default=0)
    min_stock_level = Column(Integer, default=0)
    reorder_level = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    product = relationship("models.Product")
    stock_movements = relationship("PackagedProductMovement", back_populates="packaged_product")

# Stock Movement for Raw Materials
class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"))
    movement_type = Column(Enum(StockMovementType))
    quantity = Column(Numeric(precision=10, scale=3))
    unit_price = Column(Float, nullable=True)
    total_value = Column(Float, nullable=True)
    reference_number = Column(String, nullable=True)  # PO number, SO number, etc.
    reference_type = Column(String, nullable=True)  # "purchase_order", "sales_order", etc.
    reference_id = Column(Integer, nullable=True)  # ID of the reference document
    notes = Column(Text, nullable=True)
    performed_by = Column(Integer, ForeignKey("users.id"))
    performed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    inventory_item = relationship("InventoryItem", back_populates="stock_movements")
    user = relationship("models.User", foreign_keys=[performed_by])
    purchase_receipt = relationship("PurchaseReceipt", back_populates="stock_movements", uselist=False)

# Stock Movement for Packaged Products
class PackagedProductMovement(Base):
    __tablename__ = "packaged_product_movements"

    id = Column(Integer, primary_key=True, index=True)
    packaged_product_id = Column(Integer, ForeignKey("packaged_products.id"))
    movement_type = Column(Enum(StockMovementType))
    quantity = Column(Integer)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=True)
    reference_number = Column(String, nullable=True)
    reference_type = Column(String, nullable=True)
    reference_id = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    performed_by = Column(Integer, ForeignKey("users.id"))
    performed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    packaged_product = relationship("PackagedProduct", back_populates="stock_movements")
    order = relationship("models.Order", foreign_keys=[order_id])
    order_item = relationship("models.OrderItem", foreign_keys=[order_item_id])
    user = relationship("models.User", foreign_keys=[performed_by])

# Bill of Materials (Recipe for a product)
class BillOfMaterial(Base):
    __tablename__ = "bill_of_materials"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    name = Column(String)
    description = Column(Text, nullable=True)
    version = Column(String, default="1.0")
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    product = relationship("models.Product")
    creator = relationship("models.User", foreign_keys=[created_by])
    items = relationship("BillOfMaterialItem", back_populates="bill_of_material")

# Bill of Material Items (Individual ingredients/components)
class BillOfMaterialItem(Base):
    __tablename__ = "bill_of_material_items"

    id = Column(Integer, primary_key=True, index=True)
    bom_id = Column(Integer, ForeignKey("bill_of_materials.id"))
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"))
    quantity = Column(Numeric(precision=10, scale=3))
    unit_of_measure = Column(Enum(UnitOfMeasure))
    notes = Column(Text, nullable=True)
    
    # Relationships
    bill_of_material = relationship("BillOfMaterial", back_populates="items")
    inventory_item = relationship("InventoryItem", back_populates="bom_items")

# Production Batch
class ProductionBatch(Base):
    __tablename__ = "production_batches"

    id = Column(Integer, primary_key=True, index=True)
    batch_number = Column(String, unique=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    bom_id = Column(Integer, ForeignKey("bill_of_materials.id"))
    planned_quantity = Column(Integer)
    produced_quantity = Column(Integer, default=0)
    production_date = Column(Date)
    status = Column(String)  # planned, in_progress, completed, cancelled
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    product = relationship("models.Product")
    bill_of_material = relationship("BillOfMaterial")
    creator = relationship("models.User", foreign_keys=[created_by])
    packaged_items = relationship("ProductionBatchPackaging", back_populates="production_batch")

# Production Batch Packaging (How many of each package size were produced)
class ProductionBatchPackaging(Base):
    __tablename__ = "production_batch_packaging"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("production_batches.id"))
    packaged_product_id = Column(Integer, ForeignKey("packaged_products.id"))
    quantity = Column(Integer)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    production_batch = relationship("ProductionBatch", back_populates="packaged_items")
    packaged_product = relationship("PackagedProduct")

# Supplier
class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    code = Column(String, unique=True, index=True)
    contact_person = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    gst_number = Column(String, nullable=True)
    pan_number = Column(String, nullable=True)
    payment_terms = Column(String, nullable=True)
    credit_limit = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")

# Purchase Indent (Request for purchase)
class PurchaseIndent(Base):
    __tablename__ = "purchase_indents"

    id = Column(Integer, primary_key=True, index=True)
    indent_number = Column(String, unique=True, index=True)
    requested_by = Column(Integer, ForeignKey("users.id"))
    department = Column(String, nullable=True)
    request_date = Column(Date)
    required_by_date = Column(Date, nullable=True)
    status = Column(String)  # draft, pending, approved, rejected, closed
    notes = Column(Text, nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    requester = relationship("models.User", foreign_keys=[requested_by])
    approver = relationship("models.User", foreign_keys=[approved_by])
    items = relationship("PurchaseIndentItem", back_populates="indent")

# Purchase Indent Item
class PurchaseIndentItem(Base):
    __tablename__ = "purchase_indent_items"

    id = Column(Integer, primary_key=True, index=True)
    indent_id = Column(Integer, ForeignKey("purchase_indents.id"))
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"))
    quantity = Column(Numeric(precision=10, scale=3))
    unit_of_measure = Column(Enum(UnitOfMeasure))
    estimated_price = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    indent = relationship("PurchaseIndent", back_populates="items")
    inventory_item = relationship("InventoryItem")

# Purchase Order
class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    po_number = Column(String, unique=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    indent_id = Column(Integer, ForeignKey("purchase_indents.id"), nullable=True)
    order_date = Column(Date)
    expected_delivery_date = Column(Date, nullable=True)
    delivery_address = Column(Text)
    status = Column(Enum(PurchaseOrderStatus), default=PurchaseOrderStatus.DRAFT)
    subtotal = Column(Float)
    tax_amount = Column(Float, default=0.0)
    shipping_amount = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    total_amount = Column(Float)
    payment_terms = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    supplier = relationship("Supplier", back_populates="purchase_orders")
    indent = relationship("PurchaseIndent")
    creator = relationship("models.User", foreign_keys=[created_by])
    approver = relationship("models.User", foreign_keys=[approved_by])
    items = relationship("PurchaseOrderItem", back_populates="purchase_order")
    receipts = relationship("PurchaseReceipt", back_populates="purchase_order")

# Purchase Order Item
class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, index=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.id"))
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"))
    indent_item_id = Column(Integer, ForeignKey("purchase_indent_items.id"), nullable=True)
    quantity = Column(Numeric(precision=10, scale=3))
    received_quantity = Column(Numeric(precision=10, scale=3), default=0)
    unit_of_measure = Column(Enum(UnitOfMeasure))
    unit_price = Column(Float)
    tax_rate = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    total_amount = Column(Float)
    hsn_code = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    purchase_order = relationship("PurchaseOrder", back_populates="items")
    inventory_item = relationship("InventoryItem", back_populates="purchase_order_items")
    indent_item = relationship("PurchaseIndentItem")

# Purchase Receipt (Goods Receipt Note)
class PurchaseReceipt(Base):
    __tablename__ = "purchase_receipts"

    id = Column(Integer, primary_key=True, index=True)
    receipt_number = Column(String, unique=True, index=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.id"))
    receipt_date = Column(Date)
    supplier_invoice_number = Column(String, nullable=True)
    supplier_invoice_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    received_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    purchase_order = relationship("PurchaseOrder", back_populates="receipts")
    receiver = relationship("models.User", foreign_keys=[received_by])
    items = relationship("PurchaseReceiptItem", back_populates="receipt")
    stock_movements = relationship("StockMovement", back_populates="purchase_receipt")

# Purchase Receipt Item
class PurchaseReceiptItem(Base):
    __tablename__ = "purchase_receipt_items"

    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(Integer, ForeignKey("purchase_receipts.id"))
    po_item_id = Column(Integer, ForeignKey("purchase_order_items.id"))
    received_quantity = Column(Numeric(precision=10, scale=3))
    accepted_quantity = Column(Numeric(precision=10, scale=3))
    rejected_quantity = Column(Numeric(precision=10, scale=3), default=0)
    rejection_reason = Column(Text, nullable=True)
    batch_number = Column(String, nullable=True)
    expiry_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    receipt = relationship("PurchaseReceipt", back_populates="items")
    po_item = relationship("PurchaseOrderItem")

# Gate Pass
class GatePass(Base):
    __tablename__ = "gate_passes"

    id = Column(Integer, primary_key=True, index=True)
    pass_number = Column(String, unique=True, index=True)
    pass_type = Column(Enum(GatePassType))
    pass_date = Column(Date)
    reference_number = Column(String, nullable=True)  # PO number, SO number, etc.
    reference_type = Column(String, nullable=True)  # "purchase_order", "sales_order", etc.
    reference_id = Column(Integer, nullable=True)  # ID of the reference document
    party_name = Column(String)  # Supplier or Customer name
    vehicle_number = Column(String, nullable=True)
    driver_name = Column(String, nullable=True)
    driver_contact = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    issued_by = Column(Integer, ForeignKey("users.id"))
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    issuer = relationship("models.User", foreign_keys=[issued_by])
    approver = relationship("models.User", foreign_keys=[approved_by])
    items = relationship("GatePassItem", back_populates="gate_pass")

# Gate Pass Item
class GatePassItem(Base):
    __tablename__ = "gate_pass_items"

    id = Column(Integer, primary_key=True, index=True)
    gate_pass_id = Column(Integer, ForeignKey("gate_passes.id"))
    item_type = Column(String)  # "raw_material", "packaged_product"
    item_id = Column(Integer)  # ID of inventory_item or packaged_product
    quantity = Column(Numeric(precision=10, scale=3))
    unit_of_measure = Column(String)
    description = Column(Text, nullable=True)
    
    # Relationships
    gate_pass = relationship("GatePass", back_populates="items")

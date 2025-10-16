from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date
from enum import Enum
from decimal import Decimal

from . import schemas

# Enums
class UnitOfMeasure(str, Enum):
    GRAM = "gram"
    KILOGRAM = "kilogram"
    LITER = "liter"
    MILLILITER = "milliliter"
    PIECE = "piece"
    BOX = "box"
    PACKET = "packet"
    CARTON = "carton"

class StockMovementType(str, Enum):
    PURCHASE = "purchase"
    PRODUCTION = "production"
    SALES = "sales"
    RETURN = "return"
    ADJUSTMENT = "adjustment"
    TRANSFER = "transfer"
    WASTAGE = "wastage"

class PurchaseOrderStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    CANCELLED = "cancelled"

class GatePassType(str, Enum):
    INWARD = "inward"
    OUTWARD = "outward"
    RETURN = "return"

class PackagingSize(str, Enum):
    SIZE_50G = "50g"
    SIZE_100G = "100g"
    SIZE_500G = "500g"
    SIZE_1KG = "1kg"
    CUSTOM = "custom"

# Inventory Item Schemas
class InventoryItemBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    category_id: Optional[int] = None
    unit_of_measure: UnitOfMeasure
    min_stock_level: float = 0
    max_stock_level: Optional[float] = None
    reorder_level: float = 0
    cost_price: float = 0.0
    hsn_code: Optional[str] = None
    is_active: bool = True
    is_raw_material: bool = True

class InventoryItemCreate(InventoryItemBase):
    pass

class InventoryItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    unit_of_measure: Optional[UnitOfMeasure] = None
    min_stock_level: Optional[float] = None
    max_stock_level: Optional[float] = None
    reorder_level: Optional[float] = None
    cost_price: Optional[float] = None
    hsn_code: Optional[str] = None
    is_active: Optional[bool] = None
    is_raw_material: Optional[bool] = None

class InventoryItem(InventoryItemBase):
    id: int
    current_stock: float
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

# Packaged Product Schemas
class PackagedProductBase(BaseModel):
    product_id: int
    packaging_size: PackagingSize
    custom_size: Optional[str] = None
    weight_value: float
    weight_unit: str
    items_per_package: int = 1
    barcode: Optional[str] = None
    min_stock_level: int = 0
    reorder_level: int = 0
    is_active: bool = True

class PackagedProductCreate(PackagedProductBase):
    pass

class PackagedProductUpdate(BaseModel):
    packaging_size: Optional[PackagingSize] = None
    custom_size: Optional[str] = None
    weight_value: Optional[float] = None
    weight_unit: Optional[str] = None
    items_per_package: Optional[int] = None
    barcode: Optional[str] = None
    min_stock_level: Optional[int] = None
    reorder_level: Optional[int] = None
    is_active: Optional[bool] = None

class PackagedProduct(PackagedProductBase):
    id: int
    current_stock: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    product: Optional[schemas.Product] = None
    
    class Config:
        orm_mode = True

# Stock Movement Schemas
class StockMovementBase(BaseModel):
    inventory_item_id: int
    movement_type: StockMovementType
    quantity: float
    unit_price: Optional[float] = None
    reference_number: Optional[str] = None
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    notes: Optional[str] = None

class StockMovementCreate(StockMovementBase):
    pass

class StockMovement(StockMovementBase):
    id: int
    total_value: Optional[float] = None
    performed_by: int
    performed_at: datetime
    inventory_item: Optional[InventoryItem] = None
    
    class Config:
        orm_mode = True

# Packaged Product Movement Schemas
class PackagedProductMovementBase(BaseModel):
    packaged_product_id: int
    movement_type: StockMovementType
    quantity: int
    order_id: Optional[int] = None
    order_item_id: Optional[int] = None
    reference_number: Optional[str] = None
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    notes: Optional[str] = None

class PackagedProductMovementCreate(PackagedProductMovementBase):
    pass

class PackagedProductMovement(PackagedProductMovementBase):
    id: int
    performed_by: int
    performed_at: datetime
    packaged_product: Optional[PackagedProduct] = None
    
    class Config:
        orm_mode = True

# Bill of Materials Schemas
class BillOfMaterialItemBase(BaseModel):
    inventory_item_id: int
    quantity: float
    unit_of_measure: UnitOfMeasure
    notes: Optional[str] = None

class BillOfMaterialItemCreate(BillOfMaterialItemBase):
    pass

class BillOfMaterialItem(BillOfMaterialItemBase):
    id: int
    bom_id: int
    inventory_item: Optional[InventoryItem] = None
    
    class Config:
        orm_mode = True

class BillOfMaterialBase(BaseModel):
    product_id: int
    name: str
    description: Optional[str] = None
    version: str = "1.0"
    is_active: bool = True

class BillOfMaterialCreate(BillOfMaterialBase):
    items: List[BillOfMaterialItemCreate]

class BillOfMaterial(BillOfMaterialBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    items: List[BillOfMaterialItem] = []
    
    class Config:
        orm_mode = True

# Production Batch Schemas
class ProductionBatchPackagingBase(BaseModel):
    packaged_product_id: int
    quantity: int
    notes: Optional[str] = None

class ProductionBatchPackagingCreate(ProductionBatchPackagingBase):
    pass

class ProductionBatchPackaging(ProductionBatchPackagingBase):
    id: int
    batch_id: int
    created_at: datetime
    packaged_product: Optional[PackagedProduct] = None
    
    class Config:
        orm_mode = True

class ProductionBatchBase(BaseModel):
    product_id: int
    bom_id: int
    planned_quantity: int
    production_date: date
    status: str
    notes: Optional[str] = None

class ProductionBatchCreate(ProductionBatchBase):
    packaged_items: List[ProductionBatchPackagingCreate] = []

class ProductionBatch(ProductionBatchBase):
    id: int
    batch_number: str
    produced_quantity: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    packaged_items: List[ProductionBatchPackaging] = []
    
    class Config:
        orm_mode = True

# Supplier Schemas
class SupplierBase(BaseModel):
    name: str
    code: str
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    gst_number: Optional[str] = None
    pan_number: Optional[str] = None
    payment_terms: Optional[str] = None
    credit_limit: Optional[float] = None
    is_active: bool = True
    notes: Optional[str] = None

class SupplierCreate(SupplierBase):
    pass

class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    gst_number: Optional[str] = None
    pan_number: Optional[str] = None
    payment_terms: Optional[str] = None
    credit_limit: Optional[float] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None

class Supplier(SupplierBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

# Purchase Indent Schemas
class PurchaseIndentItemBase(BaseModel):
    inventory_item_id: int
    quantity: float
    unit_of_measure: UnitOfMeasure
    estimated_price: Optional[float] = None
    notes: Optional[str] = None

class PurchaseIndentItemCreate(PurchaseIndentItemBase):
    pass

class PurchaseIndentItem(PurchaseIndentItemBase):
    id: int
    indent_id: int
    inventory_item: Optional[InventoryItem] = None
    
    class Config:
        orm_mode = True

class PurchaseIndentBase(BaseModel):
    department: Optional[str] = None
    request_date: date
    required_by_date: Optional[date] = None
    status: str
    notes: Optional[str] = None

class PurchaseIndentCreate(PurchaseIndentBase):
    items: List[PurchaseIndentItemCreate]

class PurchaseIndent(PurchaseIndentBase):
    id: int
    indent_number: str
    requested_by: int
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    items: List[PurchaseIndentItem] = []
    
    class Config:
        orm_mode = True

# Purchase Order Schemas
class PurchaseOrderItemBase(BaseModel):
    inventory_item_id: int
    indent_item_id: Optional[int] = None
    quantity: float
    unit_of_measure: UnitOfMeasure
    unit_price: float
    tax_rate: float = 0.0
    discount_amount: float = 0.0
    hsn_code: Optional[str] = None
    notes: Optional[str] = None

class PurchaseOrderItemCreate(PurchaseOrderItemBase):
    pass

class PurchaseOrderItem(PurchaseOrderItemBase):
    id: int
    po_id: int
    received_quantity: float = 0
    tax_amount: float
    total_amount: float
    inventory_item: Optional[InventoryItem] = None
    
    class Config:
        orm_mode = True

class PurchaseOrderBase(BaseModel):
    supplier_id: int
    indent_id: Optional[int] = None
    order_date: date
    expected_delivery_date: Optional[date] = None
    delivery_address: str
    status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT
    payment_terms: Optional[str] = None
    notes: Optional[str] = None

class PurchaseOrderCreate(PurchaseOrderBase):
    items: List[PurchaseOrderItemCreate]

class PurchaseOrder(PurchaseOrderBase):
    id: int
    po_number: str
    subtotal: float
    tax_amount: float
    shipping_amount: float
    discount_amount: float
    total_amount: float
    created_by: int
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    items: List[PurchaseOrderItem] = []
    supplier: Optional[Supplier] = None
    
    class Config:
        orm_mode = True

# Purchase Receipt Schemas
class PurchaseReceiptItemBase(BaseModel):
    po_item_id: int
    received_quantity: float
    accepted_quantity: float
    rejected_quantity: float = 0
    rejection_reason: Optional[str] = None
    batch_number: Optional[str] = None
    expiry_date: Optional[date] = None
    notes: Optional[str] = None

class PurchaseReceiptItemCreate(PurchaseReceiptItemBase):
    pass

class PurchaseReceiptItem(PurchaseReceiptItemBase):
    id: int
    receipt_id: int
    po_item: Optional[PurchaseOrderItem] = None
    
    class Config:
        orm_mode = True

class PurchaseReceiptBase(BaseModel):
    po_id: int
    receipt_date: date
    supplier_invoice_number: Optional[str] = None
    supplier_invoice_date: Optional[date] = None
    notes: Optional[str] = None

class PurchaseReceiptCreate(PurchaseReceiptBase):
    items: List[PurchaseReceiptItemCreate]

class PurchaseReceipt(PurchaseReceiptBase):
    id: int
    receipt_number: str
    received_by: int
    created_at: datetime
    items: List[PurchaseReceiptItem] = []
    purchase_order: Optional[PurchaseOrder] = None
    
    class Config:
        orm_mode = True

# Gate Pass Schemas
class GatePassItemBase(BaseModel):
    item_type: str  # "raw_material", "packaged_product"
    item_id: int
    quantity: float
    unit_of_measure: str
    description: Optional[str] = None

class GatePassItemCreate(GatePassItemBase):
    pass

class GatePassItem(GatePassItemBase):
    id: int
    gate_pass_id: int
    
    class Config:
        orm_mode = True

class GatePassBase(BaseModel):
    pass_type: GatePassType
    pass_date: date
    reference_number: Optional[str] = None
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    party_name: str
    vehicle_number: Optional[str] = None
    driver_name: Optional[str] = None
    driver_contact: Optional[str] = None
    notes: Optional[str] = None

class GatePassCreate(GatePassBase):
    items: List[GatePassItemCreate]

class GatePass(GatePassBase):
    id: int
    pass_number: str
    issued_by: int
    approved_by: Optional[int] = None
    created_at: datetime
    items: List[GatePassItem] = []
    
    class Config:
        orm_mode = True

# Stock Status Response
class StockStatusItem(BaseModel):
    id: int
    name: str
    code: str
    current_stock: float
    unit_of_measure: str
    min_stock_level: float
    reorder_level: float
    status: str  # "normal", "low", "critical"
    
    class Config:
        orm_mode = True

class StockStatus(BaseModel):
    items: List[StockStatusItem]
    low_stock_count: int
    critical_stock_count: int

# Packaged Product Stock Status
class PackagedProductStockItem(BaseModel):
    id: int
    product_id: int
    product_name: str
    packaging_size: str
    weight_value: float
    weight_unit: str
    current_stock: int
    min_stock_level: int
    reorder_level: int
    status: str  # "normal", "low", "critical"
    
    class Config:
        orm_mode = True

class PackagedProductStock(BaseModel):
    items: List[PackagedProductStockItem]
    low_stock_count: int
    critical_stock_count: int

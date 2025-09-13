from pydantic import BaseModel, EmailStr, Field, validator, model_validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum
import json

# Enums
class UserRole(str, Enum):
    BUYER = "buyer"
    SELLER = "seller"
    ADMIN = "admin"
    COMPANY = "company"

class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class OrderStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    REFUNDED = "refunded"
    FAILED = "failed"
    
class TaxType(str, Enum):
    GST = "gst"
    IGST = "igst"
    CGST = "cgst"
    SGST = "sgst"
    OTHER = "other"
    
class DocumentType(str, Enum):
    GST_CERTIFICATE = "gst_certificate"
    PAN_CARD = "pan_card"
    BUSINESS_LICENSE = "business_license"
    INVOICE = "invoice"
    SHIPPING_DOCUMENT = "shipping_document"
    CERTIFICATION = "certification"
    AWARD = "award"
    OTHER = "other"
    
class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    phone: Optional[str] = None
    role: UserRole = UserRole.BUYER

class BusinessDetails(BaseModel):
    business_name: str
    business_address: Dict[str, Any]  # Address as a dictionary
    gst_number: Optional[str] = None
    pan_number: Optional[str] = None
    tax_identification_number: Optional[str] = None
    bank_details: Optional[Dict[str, Any]] = None
    region: Optional[str] = None

class UserCreate(UserBase):
    password: str
    business_details: Optional[BusinessDetails] = None
    
    @validator('business_details')
    def validate_business_details(cls, v, values):
        if values.get('role') in [UserRole.SELLER, UserRole.COMPANY] and not v:
            raise ValueError('Business details are required for sellers and companies')
        return v

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    business_name: Optional[str] = None
    business_address: Optional[Dict[str, Any]] = None
    gst_number: Optional[str] = None
    pan_number: Optional[str] = None
    tax_identification_number: Optional[str] = None
    bank_details: Optional[Dict[str, Any]] = None
    region: Optional[str] = None

class UserInDB(UserBase):
    id: int
    is_active: bool
    business_name: Optional[str] = None
    business_address: Optional[Dict[str, Any]] = None
    gst_number: Optional[str] = None
    pan_number: Optional[str] = None
    tax_identification_number: Optional[str] = None
    bank_details: Optional[Dict[str, Any]] = None
    region: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        
    @validator('business_address', pre=True)
    def parse_business_address(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return v
        
    @validator('bank_details', pre=True)
    def parse_bank_details(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return v

class User(UserInDB):
    pass

# Category schemas
class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    parent_id: Optional[int] = None

class CategoryCreate(CategoryBase):
    slug: Optional[str] = None

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    parent_id: Optional[int] = None

class CategoryInDB(CategoryBase):
    id: int
    slug: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Category(CategoryInDB):
    subcategories: List["Category"] = []

# Product schemas
class GSTDetails(BaseModel):
    hsn_code: Optional[str] = None
    cgst_rate: Optional[float] = None
    sgst_rate: Optional[float] = None
    igst_rate: Optional[float] = None
    cess_rate: Optional[float] = None

class ProductBase(BaseModel):
    name: str
    description: str
    base_price: float  # Price before margin
    price: float  # Final price after margin
    stock_quantity: int = 0
    image_urls: Optional[List[str]] = None
    hsn_code: Optional[str] = None  # HSN code for GST classification
    tax_rate: Optional[float] = 0.0  # Default tax rate
    is_tax_inclusive: Optional[bool] = False  # Whether price includes tax

class ProductCreate(ProductBase):
    slug: Optional[str] = None
    sku: Optional[str] = None
    category_ids: List[int] = []
    gst_details: Optional[GSTDetails] = None
    features: Optional[List[str]] = None
    specifications: Optional[List[Dict[str, str]]] = None
    
    @model_validator(mode='before')
    def calculate_price(cls, data):
        # Calculate final price based on base price and margin
        # This is a simplified calculation - actual implementation may vary
        if isinstance(data, dict):
            base_price = data.get('base_price')
            if base_price is not None and 'price' not in data:
                # Default margin of 10% if not specified
                data['price'] = base_price * 1.1
        return data

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    base_price: Optional[float] = None
    price: Optional[float] = None
    stock_quantity: Optional[int] = None
    image_urls: Optional[List[str]] = None
    category_ids: Optional[List[int]] = None
    hsn_code: Optional[str] = None
    tax_rate: Optional[float] = None
    is_tax_inclusive: Optional[bool] = None
    gst_details: Optional[GSTDetails] = None
    approval_status: Optional[ApprovalStatus] = None
    features: Optional[List[str]] = None
    specifications: Optional[List[Dict[str, str]]] = None
    
    @model_validator(mode='before')
    def update_price(cls, data):
        # Update final price if base_price changes
        if isinstance(data, dict):
            base_price = data.get('base_price')
            if base_price is not None and 'price' not in data:
                # Default margin of 10% if not specified
                data['price'] = base_price * 1.1
        return data

class ProductInDB(ProductBase):
    id: int
    slug: str
    sku: str
    seller_id: int
    gst_details: Optional[Dict[str, Any]] = None
    features: Optional[List[str]] = None
    specifications: Optional[List[Dict[str, str]]] = None
    approval_status: ApprovalStatus
    approved_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        
    @validator('image_urls', pre=True)
    def parse_image_urls(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v or []
        
    @validator('gst_details', pre=True)
    def parse_gst_details(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v or {}

    def dict(self, *args, **kwargs):
        data = super().dict(*args, **kwargs)
        data['image_urls'] = json.dumps(data['image_urls'])
        data['gst_details'] = json.dumps(data['gst_details'])
        return data

    @classmethod
    def parse_obj(cls, obj):
        obj['image_urls'] = json.loads(obj['image_urls'])
        obj['gst_details'] = json.loads(obj['gst_details'])
        return super().parse_obj(obj)

class Product(ProductInDB):
    seller: User
    categories: List[Category] = []
    seller: User

# Cart schemas
class CartItemBase(BaseModel):
    product_id: int
    quantity: int = 1

class CartItemCreate(CartItemBase):
    pass

class CartItemUpdate(BaseModel):
    quantity: int

class CartItemInDB(CartItemBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class CartItem(CartItemInDB):
    product: Product

class Cart(BaseModel):
    items: List[CartItem] = []
    total: float = 0

# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UsernameAvailability(BaseModel):
    username: str
    available: bool
    message: str
    role: Optional[UserRole] = None

# Search schemas
class SearchQuery(BaseModel):
    query: str
    category_id: Optional[int] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    tax_inclusive_only: Optional[bool] = None
    max_tax_rate: Optional[float] = None
    buyer_state: Optional[str] = None
    seller_state: Optional[str] = 'MH'  # Default to Maharashtra
    sort_by: Optional[str] = None
    page: int = 1
    limit: int = 10

class SearchResults(BaseModel):
    results: List[Product]
    total: int
    page: int
    limit: int
    pages: int

# Address schema
class Address(BaseModel):
    street: str
    city: str
    state: str
    postal_code: str
    country: str

# Order schemas
class OrderItemBase(BaseModel):
    product_id: int
    quantity: int
    price: float

class OrderItemCreate(OrderItemBase):
    pass

class OrderItemInDB(OrderItemBase):
    id: int
    order_id: int
    seller_id: int
    total: float
    created_at: datetime

    class Config:
        from_attributes = True

class OrderItem(OrderItemInDB):
    product: Product

class OrderBase(BaseModel):
    payment_method: str
    shipping_method: str
    shipping_address: Address
    notes: Optional[str] = None

class OrderCreate(OrderBase):
    items: List[OrderItemCreate]

class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    payment_status: Optional[PaymentStatus] = None
    tracking_number: Optional[str] = None
    notes: Optional[str] = None

class OrderInDB(OrderBase):
    id: int
    order_number: str
    user_id: int
    total_amount: float
    tax_amount: float
    shipping_amount: float
    status: OrderStatus
    payment_status: PaymentStatus
    tracking_number: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Order(OrderInDB):
    user: User
    items: List[OrderItem] = []

# Order filter schemas
class OrderFilter(BaseModel):
    status: Optional[OrderStatus] = None
    payment_status: Optional[PaymentStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    search: Optional[str] = None
    page: int = 1
    limit: int = 10
    sort_by: Optional[str] = None
    sort_desc: bool = False

# File Upload Response
class FileUploadResponse(BaseModel):
    filename: str
    content_type: str
    size: int
    url: str
    folder: str
    uploaded_at: datetime

# Product Specification Schema
class ProductSpecification(BaseModel):
    name: str
    value: str

# Product Variant Schema
class ProductVariant(BaseModel):
    name: str
    price: float
    stock_quantity: int
    sku: str
    image_url: Optional[str] = None

# Seller Product List Response
class SellerProductListResponse(BaseModel):
    products: List[Product]
    total: int
    page: int
    size: int
    pages: int
    
# Product Approval Request
class ProductApprovalRequest(BaseModel):
    status: ApprovalStatus
    rejection_reason: Optional[str] = None
    
    @validator('rejection_reason')
    def validate_rejection_reason(cls, v, values):
        if values.get('status') == ApprovalStatus.REJECTED and not v:
            raise ValueError('Rejection reason is required when rejecting a product')
        return v

# Product Approval Response
class ProductApprovalResponse(BaseModel):
    product_id: int
    product_name: str
    seller_id: int
    seller_name: str
    status: ApprovalStatus
    rejection_reason: Optional[str] = None
    updated_at: datetime

# Product Approval List Response
class ProductApprovalListResponse(BaseModel):
    products: List[Product]
    total: int
    page: int
    size: int
    pages: int


# Tax Rate schemas
class TaxRateBase(BaseModel):
    tax_type: TaxType
    rate: float
    category_id: Optional[int] = None
    region: Optional[str] = None
    is_active: bool = True
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    hsn_code: Optional[str] = None

class TaxRateCreate(TaxRateBase):
    pass

class TaxRateUpdate(BaseModel):
    tax_type: Optional[TaxType] = None
    rate: Optional[float] = None
    category_id: Optional[int] = None
    region: Optional[str] = None
    is_active: Optional[bool] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    hsn_code: Optional[str] = None

class TaxRateInDB(TaxRateBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TaxRate(TaxRateInDB):
    pass


# Margin Setting schemas
class MarginSettingBase(BaseModel):
    margin_percentage: float
    product_id: Optional[int] = None
    category_id: Optional[int] = None
    seller_id: Optional[int] = None
    region: Optional[str] = None
    is_active: bool = True

class MarginSettingCreate(MarginSettingBase):
    pass

class MarginSettingUpdate(BaseModel):
    margin_percentage: Optional[float] = None
    product_id: Optional[int] = None
    category_id: Optional[int] = None
    seller_id: Optional[int] = None
    region: Optional[str] = None
    is_active: Optional[bool] = None

class MarginSettingInDB(MarginSettingBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class MarginSetting(MarginSettingInDB):
    pass


# Tax Calculation schemas
class TaxCalculationItem(BaseModel):
    product_id: int
    quantity: int = 1

class TaxCalculationRequest(BaseModel):
    product_id: int
    quantity: int = 1
    region: Optional[str] = None
    buyer_state: Optional[str] = None
    seller_state: Optional[str] = None

class OrderTaxCalculationRequest(BaseModel):
    items: List[TaxCalculationItem]
    region: Optional[str] = None
    buyer_state: Optional[str] = None
    seller_state: Optional[str] = None
    shipping_amount: float = 0
    apply_tax_to_shipping: bool = False


# Payment Method Schemas
class PaymentMethodType(str, Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    UPI = "upi"
    NET_BANKING = "net_banking"
    WALLET = "wallet"
    COD = "cash_on_delivery"
    EMI = "emi"
    BANK_TRANSFER = "bank_transfer"


class PaymentMethodBase(BaseModel):
    method_type: PaymentMethodType
    provider: str
    is_default: bool = False
    
    # Optional fields based on payment method type
    card_last_four: Optional[str] = None
    card_expiry_month: Optional[str] = None
    card_expiry_year: Optional[str] = None
    card_holder_name: Optional[str] = None
    upi_id: Optional[str] = None
    bank_name: Optional[str] = None
    account_last_four: Optional[str] = None
    account_holder_name: Optional[str] = None
    wallet_provider: Optional[str] = None
    wallet_id: Optional[str] = None


class PaymentMethodCreate(PaymentMethodBase):
    @validator('card_last_four', 'card_expiry_month', 'card_expiry_year', 'card_holder_name')
    def validate_card_details(cls, v, values):
        if values.get('method_type') in [PaymentMethodType.CREDIT_CARD, PaymentMethodType.DEBIT_CARD] and not v:
            field_name = [k for k, val in values.items() if val == v][0]
            raise ValueError(f'{field_name} is required for card payments')
        return v
    
    @validator('upi_id')
    def validate_upi(cls, v, values):
        if values.get('method_type') == PaymentMethodType.UPI and not v:
            raise ValueError('UPI ID is required for UPI payments')
        return v
    
    @validator('bank_name', 'account_last_four', 'account_holder_name')
    def validate_bank_details(cls, v, values):
        if values.get('method_type') == PaymentMethodType.BANK_TRANSFER and not v:
            field_name = [k for k, val in values.items() if val == v][0]
            raise ValueError(f'{field_name} is required for bank transfers')
        return v
    
    @validator('wallet_provider', 'wallet_id')
    def validate_wallet_details(cls, v, values):
        if values.get('method_type') == PaymentMethodType.WALLET and not v:
            field_name = [k for k, val in values.items() if val == v][0]
            raise ValueError(f'{field_name} is required for wallet payments')
        return v


class PaymentMethodUpdate(BaseModel):
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    card_expiry_month: Optional[str] = None
    card_expiry_year: Optional[str] = None
    card_holder_name: Optional[str] = None
    upi_id: Optional[str] = None
    bank_name: Optional[str] = None
    account_holder_name: Optional[str] = None
    wallet_provider: Optional[str] = None
    wallet_id: Optional[str] = None


class PaymentMethodInDB(PaymentMethodBase):
    id: int
    user_id: Optional[int] = None
    is_active: bool
    last_used: Optional[datetime] = None
    token: Optional[str] = None
    token_expiry: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PaymentMethod(PaymentMethodInDB):
    pass


# Transaction Schemas
class TransactionType(str, Enum):
    PAYMENT = "payment"
    REFUND = "refund"
    CHARGEBACK = "chargeback"
    SETTLEMENT = "settlement"
    FEE = "fee"


class TransactionBase(BaseModel):
    transaction_type: TransactionType
    amount: float
    currency: str = "INR"
    description: Optional[str] = None


class TransactionCreate(TransactionBase):
    payment_id: Optional[int] = None
    gateway: Optional[str] = None
    gateway_transaction_id: Optional[str] = None
    gateway_response: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class TransactionInDB(TransactionBase):
    id: int
    transaction_reference: str
    payment_id: Optional[int] = None
    user_id: int
    status: str
    gateway: Optional[str] = None
    gateway_transaction_id: Optional[str] = None
    gateway_response: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    transaction_date: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


class Transaction(TransactionInDB):
    pass


# Payment Schemas
class InstallmentPlanBase(BaseModel):
    total_amount: float
    number_of_installments: int
    installment_frequency: str
    interest_rate: float = 0.0
    processing_fee: float = 0.0
    start_date: datetime


class InstallmentPlanCreate(InstallmentPlanBase):
    order_id: int


class InstallmentPlanInDB(InstallmentPlanBase):
    id: int
    order_id: int
    user_id: int
    end_date: Optional[datetime] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class InstallmentPlan(InstallmentPlanInDB):
    pass


class PaymentBase(BaseModel):
    amount: float
    currency: str = "INR"
    description: Optional[str] = None


class PaymentCreate(PaymentBase):
    order_id: Optional[int] = None
    payment_method_id: Optional[int] = None
    gateway: Optional[str] = None
    due_date: Optional[datetime] = None
    
    # For installment payments
    is_installment: bool = False
    installment_plan_id: Optional[int] = None
    installment_number: Optional[int] = None
    
    # For recurring payments
    is_recurring: bool = False
    recurring_schedule: Optional[str] = None
    
    # Additional metadata
    metadata: Optional[Dict[str, Any]] = None


class PaymentUpdate(BaseModel):
    status: Optional[PaymentStatus] = None
    payment_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    description: Optional[str] = None
    gateway_payment_id: Optional[str] = None
    gateway_response: Optional[Dict[str, Any]] = None
    refunded_amount: Optional[float] = None
    refund_reason: Optional[str] = None
    next_payment_date: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class PaymentInDB(PaymentBase):
    id: int
    payment_reference: str
    order_id: Optional[int] = None
    user_id: int
    payment_method_id: Optional[int] = None
    status: PaymentStatus
    payment_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    
    # Payment gateway details
    gateway: Optional[str] = None
    gateway_payment_id: Optional[str] = None
    gateway_response: Optional[Dict[str, Any]] = None
    
    # For installment payments
    is_installment: bool
    installment_plan_id: Optional[int] = None
    installment_number: Optional[int] = None
    
    # For recurring payments
    is_recurring: bool
    recurring_schedule: Optional[str] = None
    next_payment_date: Optional[datetime] = None
    
    # For refunds
    refunded_amount: float
    refund_reason: Optional[str] = None
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class Payment(PaymentInDB):
    user: User
    order: Optional[Order] = None
    payment_method: Optional[PaymentMethod] = None
    transactions: List[Transaction] = []


class PaymentListResponse(BaseModel):
    payments: List[Payment]
    total: int
    page: int
    size: int
    pages: int


class PaymentSummary(BaseModel):
    total_payments: int
    total_amount: float
    paid_amount: float
    pending_amount: float
    refunded_amount: float
    failed_amount: float
    currency: str = "INR"
    payment_status_counts: Dict[str, int]
    recent_payments: List[Payment] = []


# Invoice Line Item schemas
class InvoiceLineItemBase(BaseModel):
    product_id: Optional[int] = None
    description: str
    quantity: float
    unit_price: float
    tax_rate: float = 0.0
    tax_amount: float = 0.0
    discount_amount: float = 0.0
    total: float
    hsn_code: Optional[str] = None


class InvoiceLineItemCreate(InvoiceLineItemBase):
    pass


class InvoiceLineItemInDB(InvoiceLineItemBase):
    id: int
    invoice_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class InvoiceLineItem(InvoiceLineItemInDB):
    product: Optional[Product] = None


# Invoice schemas
class InvoiceBase(BaseModel):
    order_id: Optional[int] = None
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    status: InvoiceStatus = InvoiceStatus.DRAFT
    
    # Financial details
    subtotal: float
    tax_amount: float
    cgst_amount: float = 0.0
    sgst_amount: float = 0.0
    igst_amount: float = 0.0
    discount_amount: float = 0.0
    shipping_amount: float = 0.0
    adjustment_amount: float = 0.0
    total_amount: float
    amount_paid: float = 0.0
    amount_due: float
    
    # Address details
    billing_address: Dict[str, Any]
    shipping_address: Optional[Dict[str, Any]] = None
    
    # Additional details
    notes: Optional[str] = None
    terms: Optional[str] = None
    payment_instructions: Optional[str] = None


class InvoiceCreate(InvoiceBase):
    line_items: List[InvoiceLineItemCreate]


class InvoiceUpdate(BaseModel):
    due_date: Optional[datetime] = None
    status: Optional[InvoiceStatus] = None
    amount_paid: Optional[float] = None
    amount_due: Optional[float] = None
    notes: Optional[str] = None
    terms: Optional[str] = None
    payment_instructions: Optional[str] = None


class InvoiceInDB(InvoiceBase):
    id: int
    invoice_number: str
    user_id: int
    seller_id: Optional[int] = None
    file_url: Optional[str] = None
    invoice_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class InvoiceResponse(InvoiceInDB):
    pass


class InvoiceDetailResponse(InvoiceInDB):
    user: User
    seller: Optional[User] = None
    order: Optional[Order] = None
    line_items: List[InvoiceLineItem] = []


class InvoiceListResponse(BaseModel):
    invoices: List[InvoiceResponse]
    total: int
    page: int
    size: int
    pages: int


class InvoiceSummary(BaseModel):
    total_invoices: int
    total_amount: float
    paid_amount: float
    pending_amount: float
    overdue_amount: float
    currency: str = "INR"
    status_counts: Dict[str, int]
    recent_invoices: List[InvoiceResponse] = []


# Seller schema for top sellers
class Seller(BaseModel):
    id: int
    username: str
    full_name: str
    business_name: str
    business_address: Optional[Dict[str, Any]] = None
    region: Optional[str] = None
    rating: Optional[float] = None
    total_sales: Optional[int] = None
    product_count: Optional[int] = None
    joined_date: Optional[datetime] = None
    verified: Optional[bool] = True
    image_url: Optional[str] = None
    
    class Config:
        from_attributes = True


# Blog schemas
class BlogBase(BaseModel):
    title: str
    content: str
    excerpt: Optional[str] = None
    featured_image: Optional[str] = None
    status: str = "draft"  # draft, published, archived
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    tags: Optional[List[str]] = None


class BlogCreate(BlogBase):
    slug: Optional[str] = None
    published_date: Optional[datetime] = None
    featured_product_ids: Optional[List[int]] = None


class BlogUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    featured_image: Optional[str] = None
    status: Optional[str] = None
    published_date: Optional[datetime] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    tags: Optional[List[str]] = None
    featured_product_ids: Optional[List[int]] = None


class BlogInDB(BlogBase):
    id: int
    slug: str
    author_id: int
    published_date: Optional[datetime] = None
    views_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Blog(BlogInDB):
    author: User
    featured_products: List[Product] = []


class BlogListResponse(BaseModel):
    blogs: List[Blog]
    total: int
    page: int
    size: int
    pages: int


# Shipping Method schemas
class ShippingMethodBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    estimated_days: str
    is_active: bool = True

class ShippingMethodCreate(ShippingMethodBase):
    pass

class ShippingMethodUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    estimated_days: Optional[str] = None
    is_active: Optional[bool] = None

class ShippingMethod(ShippingMethodBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# User Address schemas
class UserAddressBase(BaseModel):
    full_name: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    country: str
    zip_code: str
    phone_number: str
    is_default: bool = False

class UserAddressCreate(UserAddressBase):
    pass

class UserAddressUpdate(BaseModel):
    full_name: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zip_code: Optional[str] = None
    phone_number: Optional[str] = None
    is_default: Optional[bool] = None

class UserAddress(UserAddressBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

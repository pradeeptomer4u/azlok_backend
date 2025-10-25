from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, Float, DateTime, Enum, Table, JSON, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from datetime import datetime, date

from .database import Base


# User roles enum
class UserRole(str, enum.Enum):
    BUYER = "buyer"
    SELLER = "seller"
    ADMIN = "admin"
    COMPANY = "company"

# Product approval status enum
class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

# Order status enum
class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

# Payment status enum
class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    REFUNDED = "refunded"
    FAILED = "failed"
    PARTIALLY_PAID = "partially_paid"
    PROCESSING = "processing"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    
# Payment method type enum
class PaymentMethodType(str, enum.Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    UPI = "upi"
    NET_BANKING = "net_banking"
    WALLET = "wallet"
    COD = "cash_on_delivery"
    EMI = "emi"
    BANK_TRANSFER = "bank_transfer"
    
# Transaction type enum
class TransactionType(str, enum.Enum):
    PAYMENT = "payment"
    REFUND = "refund"
    CHARGEBACK = "chargeback"
    SETTLEMENT = "settlement"
    FEE = "fee"
    
# Tax type enum
class TaxType(str, enum.Enum):
    GST = "gst"
    IGST = "igst"
    CGST = "cgst"
    SGST = "sgst"
    OTHER = "other"
    
# Document type enum
class DocumentType(str, enum.Enum):
    GST_CERTIFICATE = "gst_certificate"
    PAN_CARD = "pan_card"
    BUSINESS_LICENSE = "business_license"
    INVOICE = "invoice"
    SHIPPING_DOCUMENT = "shipping_document"
    CERTIFICATION = "certification"
    AWARD = "award"
    OTHER = "other"
    
# Invoice status enum
class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    document_type = Column(Enum(DocumentType))
    file_url = Column(String)  # URL to the stored document
    user_id = Column(Integer, ForeignKey("users.id"))  # Owner of the document
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)  # Related product if any
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)  # Related order if any
    is_verified = Column(Boolean, default=False)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    verification_date = Column(DateTime(timezone=True), nullable=True)
    expiry_date = Column(DateTime(timezone=True), nullable=True)  # For documents with expiry
    doc_metadata = Column(JSON, nullable=True)  # Additional metadata - renamed from metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    verifier = relationship("User", foreign_keys=[verified_by])
    product = relationship("Product", foreign_keys=[product_id])
    order = relationship("Order", foreign_keys=[order_id])



# Association table for product categories (many-to-many)
product_category = Table(
    "product_category",
    Base.metadata,
    Column("product_id", Integer, ForeignKey("products.id"), primary_key=True),
    Column("category_id", Integer, ForeignKey("categories.id"), primary_key=True)
)

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    slug = Column(String, unique=True, index=True)
    sku = Column(String, unique=True, index=True)
    description = Column(Text)
    base_price = Column(Float)  # Base price before margin
    price = Column(Float)  # Final price after margin
    stock_quantity = Column(Integer, default=0)
    image_urls = Column(Text)  # Stored as JSON string
    seller_id = Column(Integer, ForeignKey("users.id"))
    hsn_code = Column(String, nullable=True)  # HSN code for GST classification
    tax_rate = Column(Float, default=0.0)  # Default tax rate for the product
    is_tax_inclusive = Column(Boolean, default=False)  # Whether price includes tax
    gst_details = Column(JSON, nullable=True)  # JSON with GST details
    features = Column(JSON, nullable=True)  # JSON array of feature strings
    specifications = Column(JSON, nullable=True)  # JSON array of specification objects
    approval_status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_bestseller = Column(Boolean, default=False,nullable=True)
    is_new = Column(Boolean, default=False,nullable=True)
    is_featured = Column(Boolean, default=False,nullable=True) 
    is_top_seller = Column(Boolean, default=False,nullable=True) 
    is_top_product = Column(Boolean, default=False,nullable=True) 
    is_popular  = Column(Boolean, default=False,nullable=True) 

    # Relationships
    seller = relationship("User", back_populates="products", foreign_keys=[seller_id])
    approver = relationship("User", foreign_keys=[approved_by])
    categories = relationship("Category", secondary=product_category, back_populates="products")
    cart_items = relationship("CartItem", back_populates="product")
    documents = relationship("Document", back_populates="product")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    phone = Column(String)
    role = Column(Enum(UserRole), default=UserRole.BUYER)
    is_active = Column(Boolean, default=True)
    # Business details for sellers
    business_name = Column(String, nullable=True)
    business_address = Column(Text, nullable=True)  # JSON string for address
    gst_number = Column(String, nullable=True)  # GST registration number
    pan_number = Column(String, nullable=True)  # PAN card number
    tax_identification_number = Column(String, nullable=True)  # TIN for tax purposes
    bank_details = Column(JSON, nullable=True)  # Bank account details for payments
    region = Column(String, nullable=True)  # State/region for tax calculation
    meta_data = Column(JSON, nullable=True)  # Additional metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    products = relationship("Product", back_populates="seller", foreign_keys=[Product.seller_id])
    cart_items = relationship("CartItem", back_populates="user")
    orders = relationship("Order", back_populates="user")
    documents = relationship("Document", foreign_keys=[Document.user_id], back_populates="user")
    certifications = relationship("Certification", back_populates="user")
    awards = relationship("Award", back_populates="user")
    testimonials = relationship("Testimonial", back_populates="user")
    addresses = relationship("UserAddress", back_populates="user")

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    slug = Column(String, unique=True, index=True)
    description = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Self-referential relationship for parent-child categories
    parent = relationship("Category", remote_side=[id], backref="subcategories")
    
    # Many-to-many relationship with products
    products = relationship("Product", secondary=product_category, back_populates="categories")



class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="cart_items")
    product = relationship("Product", back_populates="cart_items")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subtotal_amount = Column(Float)  # Sum of item prices before tax
    total_amount = Column(Float)  # Final amount including tax and shipping
    tax_amount = Column(Float)  # Total tax amount
    cgst_amount = Column(Float, default=0.0)  # Central GST amount
    sgst_amount = Column(Float, default=0.0)  # State GST amount
    igst_amount = Column(Float, default=0.0)  # Integrated GST amount
    shipping_amount = Column(Float)
    discount_amount = Column(Float, default=0.0)  # Total discount applied
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    payment_method = Column(String)
    payment_details = Column(Text, nullable=True)  # JSON string for payment details
    shipping_address = Column(Text)  # JSON string for address
    billing_address = Column(Text)  # JSON string for billing address
    shipping_method = Column(String)
    tracking_number = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    invoice_number = Column(String, nullable=True)  # Invoice number for tax purposes
    invoice_date = Column(DateTime(timezone=True), nullable=True)
    invoice_url = Column(String, nullable=True)  # URL to the generated invoice
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User")
    items = relationship("OrderItem", back_populates="order")
    documents = relationship("Document", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    seller_id = Column(Integer, ForeignKey("users.id"))
    quantity = Column(Integer)
    price = Column(Float)  # Price at the time of purchase
    total = Column(Float)  # price * quantity
    tax_amount = Column(Float, default=0.0)  # Total tax amount for this item
    gst_details = Column(JSON, nullable=True)  # JSON with GST breakdown (CGST, SGST, IGST)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product")
    seller = relationship("User")


class TaxRate(Base):
    __tablename__ = "tax_rates"
    
    id = Column(Integer, primary_key=True, index=True)
    tax_type = Column(Enum(TaxType))
    rate = Column(Float)  # Percentage value (e.g., 18.0 for 18%)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)  # For category-specific tax rates
    region = Column(String, nullable=True)  # For region-specific tax rates (state code)
    is_active = Column(Boolean, default=True)
    effective_from = Column(DateTime(timezone=True), server_default=func.now())
    effective_to = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    category = relationship("Category")


class MarginSetting(Base):
    __tablename__ = "margin_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    margin_percentage = Column(Float)  # Percentage value (e.g., 15.0 for 15%)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)  # For product-specific margins
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)  # For category-specific margins
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # For seller-specific margins
    region = Column(String, nullable=True)  # For region-specific margins
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    product = relationship("Product", foreign_keys=[product_id])
    category = relationship("Category", foreign_keys=[category_id])
    seller = relationship("User", foreign_keys=[seller_id])


class Certification(Base):
    __tablename__ = "certifications"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(Text, nullable=True)
    issuing_authority = Column(String)
    document_id = Column(Integer, ForeignKey("documents.id"))
    user_id = Column(Integer, ForeignKey("users.id"))  # User who earned the certification
    issue_date = Column(DateTime(timezone=True))
    expiry_date = Column(DateTime(timezone=True), nullable=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    document = relationship("Document")
    user = relationship("User")


class Award(Base):
    __tablename__ = "awards"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(Text, nullable=True)
    awarding_organization = Column(String)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))  # User who received the award
    award_date = Column(DateTime(timezone=True))
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    document = relationship("Document")
    user = relationship("User")


class PaymentMethod(Base):
    __tablename__ = "payment_methods"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    method_type = Column(Enum(PaymentMethodType))
    provider = Column(String)  # e.g., Visa, Mastercard, PayTM, PhonePe
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime(timezone=True), nullable=True)
    
    # For cards
    card_last_four = Column(String(4), nullable=True)
    card_expiry_month = Column(String(2), nullable=True)
    card_expiry_year = Column(String(4), nullable=True)
    card_holder_name = Column(String, nullable=True)
    
    # For UPI
    upi_id = Column(String, nullable=True)
    
    # For bank accounts
    bank_name = Column(String, nullable=True)
    account_last_four = Column(String(4), nullable=True)
    account_holder_name = Column(String, nullable=True)
    
    # For wallets
    wallet_provider = Column(String, nullable=True)
    wallet_id = Column(String, nullable=True)
    
    # For tokenized payments
    token = Column(String, nullable=True)  # Encrypted payment token
    token_expiry = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    payment_metadata = Column(JSON, nullable=True)  # Additional provider-specific details - renamed from metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    payments = relationship("Payment", back_populates="payment_method")


class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    payment_reference = Column(String, unique=True, index=True)  # Unique reference number
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)  # Can be null for non-order payments
    user_id = Column(Integer, ForeignKey("users.id"))
    payment_method_id = Column(Integer, ForeignKey("payment_methods.id"), nullable=True)
    amount = Column(Float)  # Total payment amount
    currency = Column(String, default="INR")
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    payment_date = Column(DateTime(timezone=True), nullable=True)  # When payment was completed
    due_date = Column(DateTime(timezone=True), nullable=True)  # For scheduled payments
    description = Column(Text, nullable=True)
    
    # Payment gateway details
    gateway = Column(String, nullable=True)  # e.g., Razorpay, Stripe
    gateway_payment_id = Column(String, nullable=True)  # ID from payment gateway
    gateway_response = Column(JSON, nullable=True)  # Full response from gateway
    gateway_order_id = Column(String, nullable=True)
    # For installment payments
    is_installment = Column(Boolean, default=False)
    installment_plan_id = Column(Integer, ForeignKey("installment_plans.id"), nullable=True)
    installment_number = Column(Integer, nullable=True)
    
    # For recurring payments
    is_recurring = Column(Boolean, default=False)
    recurring_schedule = Column(String, nullable=True)  # e.g., "monthly", "weekly"
    next_payment_date = Column(DateTime(timezone=True), nullable=True)
    
    # For refunds
    refunded_amount = Column(Float, default=0.0)
    refund_reason = Column(Text, nullable=True)
    
    # Metadata
    payment_metadata = Column(JSON, nullable=True)  # Additional payment details - renamed from metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    order = relationship("Order")
    payment_method = relationship("PaymentMethod", back_populates="payments")
    transactions = relationship("Transaction", back_populates="payment")
    invoices = relationship("Invoice", secondary="invoice_payments", back_populates="payments")


class InstallmentPlan(Base):
    __tablename__ = "installment_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    total_amount = Column(Float)  # Total amount to be paid
    number_of_installments = Column(Integer)
    installment_frequency = Column(String)  # e.g., "monthly", "weekly"
    interest_rate = Column(Float, default=0.0)  # Annual interest rate
    processing_fee = Column(Float, default=0.0)  # One-time fee
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="active")  # active, completed, defaulted
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    order = relationship("Order")
    payments = relationship("Payment")


class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_reference = Column(String, unique=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    transaction_type = Column(Enum(TransactionType))
    amount = Column(Float)
    currency = Column(String, default="INR")
    status = Column(String)  # success, failed, pending
    gateway = Column(String, nullable=True)
    gateway_transaction_id = Column(String, nullable=True)
    gateway_response = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    transaction_metadata = Column(JSON, nullable=True)  # Additional metadata - renamed from metadata
    transaction_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User")
    payment = relationship("Payment", back_populates="transactions")


class Invoice(Base):
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, unique=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)  # Can be null for non-order invoices
    user_id = Column(Integer, ForeignKey("users.id"))  # Customer
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Seller if applicable
    
    # Invoice details
    issue_date = Column(DateTime(timezone=True), server_default=func.now())
    due_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT)
    
    # Financial details
    subtotal = Column(Float)  # Sum of line items before tax
    tax_amount = Column(Float)  # Total tax amount
    cgst_amount = Column(Float, default=0.0)  # Central GST amount
    sgst_amount = Column(Float, default=0.0)  # State GST amount
    igst_amount = Column(Float, default=0.0)  # Integrated GST amount
    discount_amount = Column(Float, default=0.0)  # Total discount applied
    shipping_amount = Column(Float, default=0.0)  # Shipping charges
    adjustment_amount = Column(Float, default=0.0)  # Any other adjustments
    total_amount = Column(Float)  # Final amount including all taxes and charges
    amount_paid = Column(Float, default=0.0)  # Amount already paid
    amount_due = Column(Float)  # Remaining amount to be paid
    
    # Address details
    billing_address = Column(Text)  # JSON string for billing address
    shipping_address = Column(Text, nullable=True)  # JSON string for shipping address
    
    # Additional details
    notes = Column(Text, nullable=True)  # Invoice notes
    terms = Column(Text, nullable=True)  # Terms and conditions
    payment_instructions = Column(Text, nullable=True)  # Payment instructions
    file_url = Column(String, nullable=True)  # URL to the generated invoice PDF
    
    # Metadata
    invoice_metadata = Column(JSON, nullable=True)  # Additional invoice details
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    seller = relationship("User", foreign_keys=[seller_id])
    order = relationship("Order")
    line_items = relationship("InvoiceLineItem", back_populates="invoice")
    payments = relationship("Payment", secondary="invoice_payments", back_populates="invoices")


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)  # Can be null for custom line items
    description = Column(String)
    quantity = Column(Float)
    unit_price = Column(Float)
    tax_rate = Column(Float, default=0.0)  # Tax rate as percentage
    tax_amount = Column(Float, default=0.0)  # Tax amount for this line item
    discount_amount = Column(Float, default=0.0)  # Discount amount for this line item
    total = Column(Float)  # (unit_price * quantity) + tax_amount - discount_amount
    hsn_code = Column(String, nullable=True)  # HSN code for GST classification
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    invoice = relationship("Invoice", back_populates="line_items")
    product = relationship("Product")


# Association table for invoice-payment relationship (many-to-many)
invoice_payments = Table(
    "invoice_payments",
    Base.metadata,
    Column("invoice_id", Integer, ForeignKey("invoices.id"), primary_key=True),
    Column("payment_id", Integer, ForeignKey("payments.id"), primary_key=True),
    Column("amount", Float),  # Amount of this payment allocated to this invoice
    Column("created_at", DateTime(timezone=True), server_default=func.now())
)


class Testimonial(Base):
    """Testimonial model for customer reviews and testimonials."""
    __tablename__ = "testimonials"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    company = Column(String, nullable=False)
    image = Column(String, nullable=True)  # Path to profile image
    testimonial = Column(Text, nullable=False)  # The actual testimonial content
    rating = Column(Integer, nullable=False)  # Rating out of 5
    date = Column(Date, nullable=False, default=date.today)  # Date of testimonial
    verified = Column(Boolean, default=True)  # Whether the testimonial is verified
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Optional link to user
    meta_data = Column(JSON, nullable=True)  # Additional metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="testimonials")


# Association table for blog featured products (many-to-many)
blog_product = Table(
    "blog_product",
    Base.metadata,
    Column("blog_id", Integer, ForeignKey("blogs.id"), primary_key=True),
    Column("product_id", Integer, ForeignKey("products.id"), primary_key=True)
)


class Blog(Base):
    """Blog model for storing blog posts"""
    __tablename__ = "blogs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    slug = Column(String, unique=True, index=True)
    content = Column(Text, nullable=False)  # HTML content
    excerpt = Column(Text, nullable=True)  # Short description for previews
    featured_image = Column(String, nullable=True)  # URL to featured image
    author_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="draft")  # draft, published, archived
    published_date = Column(DateTime(timezone=True), nullable=True)
    meta_title = Column(String, nullable=True)  # For SEO
    meta_description = Column(String, nullable=True)  # For SEO
    tags = Column(JSON, nullable=True)  # Array of tags
    views_count = Column(Integer, default=0)  # Number of views
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    author = relationship("User", backref="blogs")
    featured_products = relationship("Product", secondary=blog_product, backref="featured_in_blogs")


class ShippingMethod(Base):
    __tablename__ = "shipping_methods"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    estimated_days = Column(String, nullable=False)  # e.g., "3-5 days", "1-2 days"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class UserAddress(Base):
    __tablename__ = "user_addresses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    full_name = Column(String, nullable=False)
    address_line1 = Column(String, nullable=False)
    address_line2 = Column(String, nullable=True)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    country = Column(String, nullable=False)
    zip_code = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    user = relationship("User", back_populates="addresses")


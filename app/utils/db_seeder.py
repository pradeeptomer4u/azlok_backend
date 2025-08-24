"""
Database seeder utility to populate the database with initial data.
"""
import os
import sys
import json
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import random
import string

# Add the parent directory to sys.path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app import models, schemas
from app.database import SessionLocal, engine, Base
from app.utils.slug_generator import generate_slug

# Create all tables if they don't exist
Base.metadata.create_all(bind=engine)

# Mock product data from frontend
mock_products = [
    {
        "id": 1,
        "name": "Industrial Machinery Part XYZ",
        "image": "/globe.svg",
        "slug": "industrial-machinery-part-xyz",
        "price": 12500,
        "minOrder": 5,
        "seller": "ABC Manufacturing",
        "location": "Delhi, India"
    },
    {
        "id": 2,
        "name": "Premium Cotton Fabric",
        "image": "/globe.svg",
        "slug": "premium-cotton-fabric",
        "price": 450,
        "minOrder": 100,
        "seller": "Textile World Ltd",
        "location": "Mumbai, India"
    },
    {
        "id": 3,
        "name": "LED Panel Lights (Pack of 10)",
        "image": "/globe.svg",
        "slug": "led-panel-lights-pack",
        "price": 2200,
        "minOrder": 10,
        "seller": "Bright Electronics",
        "location": "Bangalore, India"
    },
    {
        "id": 4,
        "name": "Stainless Steel Kitchen Equipment",
        "image": "/globe.svg",
        "slug": "stainless-steel-kitchen-equipment",
        "price": 18500,
        "minOrder": 2,
        "seller": "Kitchen Pro Solutions",
        "location": "Chennai, India"
    },
    {
        "id": 5,
        "name": "Organic Food Ingredients",
        "image": "/globe.svg",
        "slug": "organic-food-ingredients",
        "price": 750,
        "minOrder": 25,
        "seller": "Natural Foods Inc",
        "location": "Kolkata, India"
    },
    {
        "id": 6,
        "name": "Office Furniture Set",
        "image": "/globe.svg",
        "slug": "office-furniture-set",
        "price": 35000,
        "minOrder": 1,
        "seller": "Modern Interiors",
        "location": "Hyderabad, India"
    },
    {
        "id": 7,
        "name": "Industrial Safety Equipment",
        "image": "/globe.svg",
        "slug": "industrial-safety-equipment",
        "price": 4500,
        "minOrder": 10,
        "seller": "SafetyFirst Corp",
        "location": "Pune, India"
    },
    {
        "id": 8,
        "name": "Pharmaceutical Raw Materials",
        "image": "/globe.svg",
        "slug": "pharmaceutical-raw-materials",
        "price": 8900,
        "minOrder": 50,
        "seller": "MediChem Supplies",
        "location": "Ahmedabad, India"
    },
    {
        "id": 9,
        "name": "Smart Home Security System",
        "image": "/globe.svg",
        "slug": "smart-home-security-system",
        "price": 15999,
        "minOrder": 1,
        "seller": "Bright Electronics",
        "location": "Bangalore, India"
    },
    {
        "id": 10,
        "name": "Commercial Coffee Machine",
        "image": "/globe.svg",
        "slug": "commercial-coffee-machine",
        "price": 42500,
        "minOrder": 1,
        "seller": "Kitchen Pro Solutions",
        "location": "Chennai, India"
    },
    {
        "id": 11,
        "name": "Ergonomic Office Chair",
        "image": "/globe.svg",
        "slug": "ergonomic-office-chair",
        "price": 8750,
        "minOrder": 4,
        "seller": "Modern Interiors",
        "location": "Hyderabad, India"
    },
    {
        "id": 12,
        "name": "Silk Fabric Bundle",
        "image": "/globe.svg",
        "slug": "silk-fabric-bundle",
        "price": 1200,
        "minOrder": 50,
        "seller": "Textile World Ltd",
        "location": "Mumbai, India"
    },
    {
        "id": 13,
        "name": "Industrial CNC Machine",
        "image": "/globe.svg",
        "slug": "industrial-cnc-machine",
        "price": 185000,
        "minOrder": 1,
        "seller": "ABC Manufacturing",
        "location": "Delhi, India"
    },
    {
        "id": 14,
        "name": "Organic Spice Collection",
        "image": "/globe.svg",
        "slug": "organic-spice-collection",
        "price": 1850,
        "minOrder": 10,
        "seller": "Natural Foods Inc",
        "location": "Kolkata, India"
    },
    {
        "id": 15,
        "name": "Fire Resistant Workwear Set",
        "image": "/globe.svg",
        "slug": "fire-resistant-workwear-set",
        "price": 3200,
        "minOrder": 5,
        "seller": "SafetyFirst Corp",
        "location": "Pune, India"
    },
    {
        "id": 16,
        "name": "Medical Grade Disinfectant",
        "image": "/globe.svg",
        "slug": "medical-grade-disinfectant",
        "price": 1200,
        "minOrder": 20,
        "seller": "MediChem Supplies",
        "location": "Ahmedabad, India"
    }
]

# Mock categories
mock_categories = [
    {"name": "Industrial Supplies", "slug": "industrial-supplies", "description": "Industrial machinery, parts, and equipment"},
    {"name": "Textiles", "slug": "textiles", "description": "Fabrics, clothing materials, and textile products"},
    {"name": "Electronics", "slug": "electronics", "description": "Electronic components, devices, and equipment"},
    {"name": "Kitchen Equipment", "slug": "kitchen-equipment", "description": "Commercial and residential kitchen equipment"},
    {"name": "Food & Beverages", "slug": "food-beverages", "description": "Food ingredients, beverages, and related products"},
    {"name": "Furniture", "slug": "furniture", "description": "Office and home furniture"},
    {"name": "Safety Equipment", "slug": "safety-equipment", "description": "Industrial and personal safety equipment"},
    {"name": "Pharmaceuticals", "slug": "pharmaceuticals", "description": "Pharmaceutical ingredients and products"}
]

def generate_random_sku():
    """Generate a random SKU code."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def create_admin_user(db: Session):
    """Create admin users if they don't exist."""
    admin_users = [
        {
            "email": "admin@example.com",
            "username": "admin",
            "full_name": "Admin User",
            "phone": "+911234567890",
            "department": "IT",
            "designation": "System Administrator"
        },
        {
            "email": "finance_admin@example.com",
            "username": "finance_admin",
            "full_name": "Finance Admin",
            "phone": "+911234567891",
            "department": "Finance",
            "designation": "Finance Manager"
        },
        {
            "email": "sales_admin@example.com",
            "username": "sales_admin",
            "full_name": "Sales Admin",
            "phone": "+911234567892",
            "department": "Sales",
            "designation": "Sales Manager"
        },
        {
            "email": "support_admin@example.com",
            "username": "support_admin",
            "full_name": "Support Admin",
            "phone": "+911234567893",
            "department": "Customer Support",
            "designation": "Support Manager"
        },
        {
            "email": "logistics_admin@example.com",
            "username": "logistics_admin",
            "full_name": "Logistics Admin",
            "phone": "+911234567894",
            "department": "Logistics",
            "designation": "Logistics Manager"
        }
    ]
    
    created_admins = []
    
    for admin_data in admin_users:
        admin = db.query(models.User).filter(models.User.email == admin_data["email"]).first()
        
        if not admin:
            admin = models.User(
                email=admin_data["email"],
                username=admin_data["username"],
                hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "password"
                full_name=admin_data["full_name"],
                phone=admin_data["phone"],
                role=models.UserRole.ADMIN,
                is_active=True,
                meta_data={
                    "department": admin_data["department"],
                    "designation": admin_data["designation"]
                }
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            created_admins.append(admin)
            print(f"Created admin user: {admin.email} ({admin_data['department']})")
        else:
            created_admins.append(admin)
            print(f"Admin user already exists: {admin.email}")
    
    return created_admins

def create_seller_users(db: Session):
    """Create seller users based on mock product data."""
    sellers = {}
    
    for product in mock_products:
        seller_name = product["seller"]
        if seller_name not in sellers:
            # Create a normalized username from seller name
            username = seller_name.lower().replace(' ', '_').replace('.', '_')
            email = f"{username}@example.com"
            
            # Check if seller already exists
            existing_seller = db.query(models.User).filter(models.User.email == email).first()
            
            if not existing_seller:
                # Extract location (city) from the product location
                location = product["location"].split(',')[0].strip()
                
                seller = models.User(
                    email=email,
                    username=username,
                    hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "password"
                    full_name=seller_name,
                    phone=f"+91{random.randint(7000000000, 9999999999)}",
                    role=models.UserRole.SELLER,
                    is_active=True,
                    business_name=seller_name,
                    business_address=json.dumps({
                        "street": f"{random.randint(1, 100)} Business Park",
                        "city": location,
                        "state": "Maharashtra" if location == "Mumbai" else "Karnataka" if location == "Bangalore" else "Tamil Nadu" if location == "Chennai" else "Delhi",
                        "postal_code": f"{random.randint(100000, 999999)}",
                        "country": "India"
                    }),
                    gst_number=f"27{random.randint(10000000000, 99999999999)}",
                    region=location
                )
                db.add(seller)
                db.commit()
                db.refresh(seller)
                sellers[seller_name] = seller
                print(f"Created seller: {seller.email}")
            else:
                sellers[seller_name] = existing_seller
                print(f"Seller already exists: {existing_seller.email}")
    
    return sellers

def create_buyer_users(db: Session, count=5):
    """Create some buyer users."""
    buyers = []
    cities = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad", "Kolkata", "Pune", "Ahmedabad"]
    
    for i in range(1, count + 1):
        email = f"buyer{i}@example.com"
        existing_buyer = db.query(models.User).filter(models.User.email == email).first()
        
        if not existing_buyer:
            city = random.choice(cities)
            buyer = models.User(
                email=email,
                username=f"buyer{i}",
                hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "password"
                full_name=f"Buyer User {i}",
                phone=f"+91{random.randint(7000000000, 9999999999)}",
                role=models.UserRole.BUYER,
                is_active=True,
                region=city
            )
            db.add(buyer)
            db.commit()
            db.refresh(buyer)
            buyers.append(buyer)
            print(f"Created buyer: {buyer.email}")
        else:
            buyers.append(existing_buyer)
            print(f"Buyer already exists: {existing_buyer.email}")
    
    return buyers

def create_categories(db: Session):
    """Create product categories."""
    categories = {}
    
    for cat_data in mock_categories:
        existing_category = db.query(models.Category).filter(models.Category.slug == cat_data["slug"]).first()
        
        if not existing_category:
            category = models.Category(
                name=cat_data["name"],
                slug=cat_data["slug"],
                description=cat_data["description"],
                image_url="/globe.svg"  # Placeholder image
            )
            db.add(category)
            db.commit()
            db.refresh(category)
            categories[cat_data["name"]] = category
            print(f"Created category: {category.name}")
        else:
            categories[cat_data["name"]] = existing_category
            print(f"Category already exists: {existing_category.name}")
    
    return categories

def create_products(db: Session, sellers, categories):
    """Create products based on mock data."""
    products = []
    
    for product_data in mock_products:
        existing_product = db.query(models.Product).filter(models.Product.slug == product_data["slug"]).first()
        
        if not existing_product:
            # Find the seller
            seller = sellers.get(product_data["seller"])
            if not seller:
                print(f"Seller not found for product: {product_data['name']}")
                continue
            
            # Determine the category based on product name
            category_name = None
            if "Machinery" in product_data["name"]:
                category_name = "Industrial Supplies"
            elif "Cotton" in product_data["name"] or "Fabric" in product_data["name"]:
                category_name = "Textiles"
            elif "LED" in product_data["name"] or "Electronics" in product_data["name"]:
                category_name = "Electronics"
            elif "Kitchen" in product_data["name"]:
                category_name = "Kitchen Equipment"
            elif "Food" in product_data["name"] or "Organic" in product_data["name"]:
                category_name = "Food & Beverages"
            elif "Furniture" in product_data["name"]:
                category_name = "Furniture"
            elif "Safety" in product_data["name"]:
                category_name = "Safety Equipment"
            elif "Pharmaceutical" in product_data["name"]:
                category_name = "Pharmaceuticals"
            else:
                # Default to first category if no match
                category_name = list(categories.keys())[0]
            
            category = categories.get(category_name)
            
            # Generate a description
            description = f"{product_data['name']} - High quality product from {product_data['seller']}. " \
                         f"Minimum order quantity: {product_data['minOrder']} units. " \
                         f"Shipped from {product_data['location']}."
            
            # Create the product
            product = models.Product(
                name=product_data["name"],
                slug=product_data["slug"],
                sku=generate_random_sku(),
                description=description,
                base_price=product_data["price"] * 0.8,  # 20% margin
                price=product_data["price"],
                stock_quantity=random.randint(50, 500),
                image_urls=json.dumps([product_data["image"]]),
                seller_id=seller.id,
                hsn_code=f"{random.randint(1000, 9999)}",
                tax_rate=18.0,  # Default GST rate
                is_tax_inclusive=False,
                gst_details=json.dumps({
                    "cgst": 9.0,
                    "sgst": 9.0,
                    "igst": 18.0
                }),
                approval_status=models.ApprovalStatus.APPROVED,
                approved_by=1  # Admin user ID
            )
            
            db.add(product)
            db.commit()
            db.refresh(product)
            
            # Add category to product
            if category:
                product.categories.append(category)
                db.commit()
            
            products.append(product)
            print(f"Created product: {product.name}")
        else:
            products.append(existing_product)
            print(f"Product already exists: {existing_product.name}")
    
    return products

def create_orders_and_invoices(db: Session, buyers, products):
    """Create sample orders and invoices for buyers."""
    for buyer in buyers:
        # Create 1-3 orders per buyer
        for _ in range(random.randint(1, 3)):
            # Select 1-4 random products for this order
            order_products = random.sample(products, random.randint(1, 4))
            
            # Calculate order totals
            subtotal = 0
            tax_amount = 0
            
            # Create order
            order_number = f"ORD-{datetime.now().strftime('%Y%m')}-{random.randint(1000, 9999)}"
            
            # Create shipping and billing addresses
            address = {
                "street": f"{random.randint(1, 100)} {random.choice(['Main St', 'Park Avenue', 'Gandhi Road', 'MG Road'])}",
                "city": buyer.region or "Mumbai",
                "state": "Maharashtra" if buyer.region == "Mumbai" else "Karnataka" if buyer.region == "Bangalore" else "Tamil Nadu" if buyer.region == "Chennai" else "Delhi",
                "postal_code": f"{random.randint(100000, 999999)}",
                "country": "India"
            }
            
            order = models.Order(
                order_number=order_number,
                user_id=buyer.id,
                subtotal_amount=0,  # Will update after adding items
                total_amount=0,  # Will update after adding items
                tax_amount=0,  # Will update after adding items
                shipping_amount=random.choice([0, 100, 150, 200]),
                status=random.choice(list(models.OrderStatus)),
                payment_status=random.choice(list(models.PaymentStatus)),
                payment_method=random.choice(["credit_card", "debit_card", "upi", "net_banking"]),
                shipping_address=json.dumps(address),
                billing_address=json.dumps(address),
                shipping_method=random.choice(["standard", "express", "same_day"]),
                notes="Sample order created by database seeder"
            )
            
            db.add(order)
            db.commit()
            db.refresh(order)
            
            # Add order items
            for product in order_products:
                quantity = random.randint(1, 5)
                price = product.price
                item_total = price * quantity
                item_tax = item_total * (product.tax_rate / 100)
                
                order_item = models.OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    seller_id=product.seller_id,
                    quantity=quantity,
                    price=price,
                    total=item_total,
                    tax_amount=item_tax,
                    gst_details=json.dumps({
                        "cgst": item_tax / 2,
                        "sgst": item_tax / 2,
                        "igst": 0
                    })
                )
                
                db.add(order_item)
                subtotal += item_total
                tax_amount += item_tax
            
            # Update order totals
            total_amount = subtotal + tax_amount + order.shipping_amount
            order.subtotal_amount = subtotal
            order.tax_amount = tax_amount
            order.total_amount = total_amount
            
            # Create invoice if order is not pending
            if order.status != models.OrderStatus.PENDING:
                invoice_number = f"INV-{datetime.now().strftime('%Y%m')}-{random.randint(1000, 9999)}"
                
                invoice = models.Invoice(
                    invoice_number=invoice_number,
                    order_id=order.id,
                    user_id=buyer.id,
                    issue_date=datetime.now(),
                    due_date=datetime.now(),
                    status=models.InvoiceStatus.ISSUED if order.payment_status == models.PaymentStatus.PENDING else models.InvoiceStatus.PAID,
                    subtotal=subtotal,
                    tax_amount=tax_amount,
                    cgst_amount=tax_amount / 2,
                    sgst_amount=tax_amount / 2,
                    shipping_amount=order.shipping_amount,
                    total_amount=total_amount,
                    amount_paid=total_amount if order.payment_status == models.PaymentStatus.PAID else 0,
                    amount_due=0 if order.payment_status == models.PaymentStatus.PAID else total_amount,
                    billing_address=order.billing_address,
                    shipping_address=order.shipping_address,
                    notes="Thank you for your business!",
                    terms="Payment due within 30 days.",
                    payment_instructions="Please make payment to the account details provided in the invoice."
                )
                
                db.add(invoice)
                db.commit()
                db.refresh(invoice)
                
                # Add invoice line items
                for order_item in order.items:
                    line_item = models.InvoiceLineItem(
                        invoice_id=invoice.id,
                        product_id=order_item.product_id,
                        description=db.query(models.Product).get(order_item.product_id).name,
                        quantity=order_item.quantity,
                        unit_price=order_item.price,
                        tax_rate=db.query(models.Product).get(order_item.product_id).tax_rate,
                        tax_amount=order_item.tax_amount,
                        total=order_item.total + order_item.tax_amount,
                        hsn_code=db.query(models.Product).get(order_item.product_id).hsn_code
                    )
                    
                    db.add(line_item)
                
                # Update order with invoice information
                order.invoice_number = invoice_number
                order.invoice_date = invoice.issue_date
                
                db.commit()
                print(f"Created invoice: {invoice.invoice_number} for order: {order.order_number}")
            
            db.commit()
            print(f"Created order: {order.order_number}")

def create_tax_rates(db: Session):
    """Create tax rate master entries."""
    tax_rates = [
        # Standard GST rates
        {"tax_type": models.TaxType.GST, "rate": 5.0, "description": "GST 5%"},
        {"tax_type": models.TaxType.GST, "rate": 12.0, "description": "GST 12%"},
        {"tax_type": models.TaxType.GST, "rate": 18.0, "description": "GST 18%"},
        {"tax_type": models.TaxType.GST, "rate": 28.0, "description": "GST 28%"},
        
        # Category-specific tax rates
        {"tax_type": models.TaxType.GST, "rate": 5.0, "description": "Food & Beverages GST", "category_name": "Food & Beverages"},
        {"tax_type": models.TaxType.GST, "rate": 12.0, "description": "Textiles GST", "category_name": "Textiles"},
        {"tax_type": models.TaxType.GST, "rate": 18.0, "description": "Electronics GST", "category_name": "Electronics"},
        {"tax_type": models.TaxType.GST, "rate": 28.0, "description": "Luxury Items GST", "category_name": "Furniture"},
        
        # Region-specific tax rates
        {"tax_type": models.TaxType.GST, "rate": 18.0, "description": "Maharashtra GST", "region": "Maharashtra"},
        {"tax_type": models.TaxType.GST, "rate": 18.0, "description": "Karnataka GST", "region": "Karnataka"},
        {"tax_type": models.TaxType.GST, "rate": 18.0, "description": "Delhi GST", "region": "Delhi"},
    ]
    
    created_tax_rates = []
    
    for tax_data in tax_rates:
        category_id = None
        if "category_name" in tax_data:
            category = db.query(models.Category).filter(models.Category.name == tax_data["category_name"]).first()
            if category:
                category_id = category.id
            del tax_data["category_name"]
        
        # Check if tax rate already exists
        existing_tax = db.query(models.TaxRate).filter(
            models.TaxRate.tax_type == tax_data["tax_type"],
            models.TaxRate.rate == tax_data["rate"],
            models.TaxRate.category_id == category_id,
            models.TaxRate.region == tax_data.get("region")
        ).first()
        
        if not existing_tax:
            tax_rate = models.TaxRate(
                tax_type=tax_data["tax_type"],
                rate=tax_data["rate"],
                category_id=category_id,
                region=tax_data.get("region"),
                is_active=True,
                effective_from=datetime.now()
            )
            
            db.add(tax_rate)
            db.commit()
            db.refresh(tax_rate)
            created_tax_rates.append(tax_rate)
            print(f"Created tax rate: {tax_data['description']} - {tax_rate.rate}%")
        else:
            created_tax_rates.append(existing_tax)
            print(f"Tax rate already exists: {tax_data['description']} - {existing_tax.rate}%")
    
    return created_tax_rates

def create_margin_settings(db: Session, categories):
    """Create margin setting master entries."""
    margin_settings = [
        # Default margins
        {"margin_percentage": 10.0, "description": "Default margin"},
        
        # Category-specific margins
        {"margin_percentage": 15.0, "description": "Electronics margin", "category_name": "Electronics"},
        {"margin_percentage": 20.0, "description": "Furniture margin", "category_name": "Furniture"},
        {"margin_percentage": 8.0, "description": "Food & Beverages margin", "category_name": "Food & Beverages"},
        {"margin_percentage": 12.0, "description": "Textiles margin", "category_name": "Textiles"},
        
        # Region-specific margins
        {"margin_percentage": 12.0, "description": "Mumbai margin", "region": "Mumbai"},
        {"margin_percentage": 10.0, "description": "Delhi margin", "region": "Delhi"},
        {"margin_percentage": 11.0, "description": "Bangalore margin", "region": "Bangalore"},
    ]
    
    created_margins = []
    
    for margin_data in margin_settings:
        category_id = None
        if "category_name" in margin_data:
            category = db.query(models.Category).filter(models.Category.name == margin_data["category_name"]).first()
            if category:
                category_id = category.id
            del margin_data["category_name"]
        
        # Check if margin setting already exists
        existing_margin = db.query(models.MarginSetting).filter(
            models.MarginSetting.margin_percentage == margin_data["margin_percentage"],
            models.MarginSetting.category_id == category_id,
            models.MarginSetting.region == margin_data.get("region")
        ).first()
        
        if not existing_margin:
            margin = models.MarginSetting(
                margin_percentage=margin_data["margin_percentage"],
                category_id=category_id,
                region=margin_data.get("region"),
                is_active=True
            )
            
            db.add(margin)
            db.commit()
            db.refresh(margin)
            created_margins.append(margin)
            print(f"Created margin setting: {margin_data['description']} - {margin.margin_percentage}%")
        else:
            created_margins.append(existing_margin)
            print(f"Margin setting already exists: {margin_data['description']} - {existing_margin.margin_percentage}%")
    
    return created_margins

def create_payment_methods(db: Session, buyers):
    """Create payment method master entries for buyers."""
    payment_method_types = [
        (models.PaymentMethodType.CREDIT_CARD, "Visa"),
        (models.PaymentMethodType.CREDIT_CARD, "Mastercard"),
        (models.PaymentMethodType.DEBIT_CARD, "Visa Debit"),
        (models.PaymentMethodType.DEBIT_CARD, "RuPay"),
        (models.PaymentMethodType.UPI, "Google Pay"),
        (models.PaymentMethodType.UPI, "PhonePe"),
        (models.PaymentMethodType.UPI, "Paytm UPI"),
        (models.PaymentMethodType.WALLET, "Paytm Wallet"),
        (models.PaymentMethodType.WALLET, "Amazon Pay"),
        (models.PaymentMethodType.NET_BANKING, "HDFC Bank"),
        (models.PaymentMethodType.NET_BANKING, "ICICI Bank"),
        (models.PaymentMethodType.NET_BANKING, "SBI"),
    ]
    
    created_payment_methods = []
    
    # Create 1-3 payment methods for each buyer
    for buyer in buyers:
        # Select 1-3 random payment method types
        selected_methods = random.sample(payment_method_types, random.randint(1, 3))
        
        for method_type, provider in selected_methods:
            # Check if payment method already exists
            existing_method = db.query(models.PaymentMethod).filter(
                models.PaymentMethod.user_id == buyer.id,
                models.PaymentMethod.method_type == method_type,
                models.PaymentMethod.provider == provider
            ).first()
            
            if not existing_method:
                payment_method = models.PaymentMethod(
                    user_id=buyer.id,
                    method_type=method_type,
                    provider=provider,
                    is_default=False,  # Will set one as default later
                    is_active=True
                )
                
                # Add type-specific details
                if method_type in [models.PaymentMethodType.CREDIT_CARD, models.PaymentMethodType.DEBIT_CARD]:
                    payment_method.card_last_four = ''.join(random.choices(string.digits, k=4))
                    payment_method.card_expiry_month = f"{random.randint(1, 12):02d}"
                    payment_method.card_expiry_year = str(random.randint(2025, 2030))
                    payment_method.card_holder_name = buyer.full_name
                elif method_type == models.PaymentMethodType.UPI:
                    payment_method.upi_id = f"{buyer.username.lower()}@{provider.lower().replace(' ', '')}"
                elif method_type == models.PaymentMethodType.NET_BANKING:
                    payment_method.bank_name = provider
                    payment_method.account_last_four = ''.join(random.choices(string.digits, k=4))
                    payment_method.account_holder_name = buyer.full_name
                
                db.add(payment_method)
                created_payment_methods.append(payment_method)
                print(f"Created payment method: {method_type.value} - {provider} for {buyer.email}")
            else:
                created_payment_methods.append(existing_method)
                print(f"Payment method already exists: {method_type.value} - {provider} for {buyer.email}")
        
        # Set one payment method as default for each buyer
        if created_payment_methods:
            buyer_methods = [pm for pm in created_payment_methods if pm.user_id == buyer.id]
            if buyer_methods:
                default_method = random.choice(buyer_methods)
                default_method.is_default = True
                print(f"Set default payment method for {buyer.email}: {default_method.method_type.value} - {default_method.provider}")
    
    db.commit()
    return created_payment_methods

def create_testimonials(db: Session, buyers):
    """Create testimonials from buyers and other users."""
    testimonials_data = [
        {
            "name": "Rajesh Kumar",
            "company": "Tech Solutions Pvt Ltd",
            "image": "/testimonials/person1.jpg",
            "testimonial": "Azlok Enterprises has transformed how we source our electronic components. The platform is intuitive, and the quality of suppliers is exceptional. Our procurement process is now 40% faster.",
            "rating": 5,
            "date": "2025-07-15",
            "verified": True
        },
        {
            "name": "Priya Sharma",
            "company": "Global Textiles Manufacturing",
            "image": "/testimonials/person2.jpg",
            "testimonial": "As a textile manufacturer, finding reliable raw material suppliers was always challenging. Since joining Azlok, we've connected with verified suppliers who deliver consistent quality. Highly recommended!",
            "rating": 5,
            "date": "2025-07-22",
            "verified": True
        },
        {
            "name": "Vikram Singh",
            "company": "Innovative Machinery Ltd",
            "image": "/testimonials/person3.jpg",
            "testimonial": "The seller verification process on Azlok gives us confidence when making large purchases. We've expanded our business network significantly and found new clients through the platform.",
            "rating": 4,
            "date": "2025-08-01",
            "verified": True
        },
        {
            "name": "Ananya Patel",
            "company": "Organic Foods Export",
            "image": "/testimonials/person4.jpg",
            "testimonial": "Azlok's platform helped us reach international buyers we couldn't access before. The product approval workflow ensures that only quality products are listed, maintaining high standards.",
            "rating": 5,
            "date": "2025-08-05",
            "verified": True
        },
        {
            "name": "Suresh Menon",
            "company": "Healthcare Supplies Co.",
            "image": "/testimonials/person5.jpg",
            "testimonial": "The invoice management system on Azlok has streamlined our accounting process. We can now generate and track invoices effortlessly, saving hours of administrative work each week.",
            "rating": 5,
            "date": "2025-08-10",
            "verified": True
        },
        {
            "name": "Meera Kapoor",
            "company": "Sustainable Packaging Solutions",
            "image": "/testimonials/person6.jpg",
            "testimonial": "As a small business, we appreciate how Azlok has made tax compliance easier. The automated GST calculations and documentation have reduced our compliance burden significantly.",
            "rating": 4,
            "date": "2025-08-12",
            "verified": True
        },
        {
            "name": "Arjun Reddy",
            "company": "Modern Office Interiors",
            "image": "/testimonials/person7.jpg",
            "testimonial": "The payment processing on Azlok is secure and efficient. Multiple payment options make it convenient for our customers, and the transaction history is well-organized for our records.",
            "rating": 5,
            "date": "2025-08-15",
            "verified": True
        },
        {
            "name": "Neha Gupta",
            "company": "Safety Equipment Distributors",
            "image": "/testimonials/person8.jpg",
            "testimonial": "We've been using Azlok for over six months now, and the platform keeps improving. The recent updates to the product management features have made listing and updating our inventory much faster.",
            "rating": 5,
            "date": "2025-08-20",
            "verified": True
        }
    ]
    
    created_testimonials = []
    
    # Link some testimonials to actual buyer users
    for i, testimonial_data in enumerate(testimonials_data):
        # Try to link to a buyer if available (for the first few testimonials)
        user = None
        if i < len(buyers) and i < 4:  # Link first 4 testimonials to buyers if possible
            user = buyers[i]
        
        # Parse the date string to a date object
        date_obj = datetime.strptime(testimonial_data["date"], "%Y-%m-%d").date()
        
        testimonial = models.Testimonial(
            name=testimonial_data["name"],
            company=testimonial_data["company"],
            image=testimonial_data["image"],
            testimonial=testimonial_data["testimonial"],
            rating=testimonial_data["rating"],
            date=date_obj,
            verified=testimonial_data["verified"],
            user_id=user.id if user else None,
            meta_data={
                "source": "seeder",
                "featured": i < 4  # Mark first 4 as featured
            }
        )
        
        db.add(testimonial)
        created_testimonials.append(testimonial)
    
    db.commit()
    for testimonial in created_testimonials:
        db.refresh(testimonial)
    
    print(f"Created {len(created_testimonials)} testimonials")
    return created_testimonials


def seed_database():
    """Main function to seed the database."""
    db = SessionLocal()
    try:
        print("Starting database seeding...")
        
        # Create users
        admins = create_admin_user(db)
        sellers = create_seller_users(db)
        buyers = create_buyer_users(db)
        
        # Create categories
        categories = create_categories(db)
        
        # Create tax and GST master entries
        tax_rates = create_tax_rates(db)
        
        # Create margin settings
        margins = create_margin_settings(db, categories)
        
        # Create products
        products = create_products(db, sellers, categories)
        
        # Create payment methods
        payment_methods = create_payment_methods(db, buyers)
        
        # Create orders and invoices
        create_orders_and_invoices(db, buyers, products)
        
        # Create testimonials
        testimonials = create_testimonials(db, buyers)
        
        print("Database seeding completed successfully!")
    except Exception as e:
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()

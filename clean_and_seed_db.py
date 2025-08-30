#!/usr/bin/env python3
"""
Clean database and create sample products with relevant images
"""
import os
import sys
import json
from datetime import datetime
from sqlalchemy.orm import Session

# Add the parent directory to sys.path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from app import models
from app.database import SessionLocal, engine, Base
from app.routers.auth import get_password_hash

# Create all tables if they don't exist
Base.metadata.create_all(bind=engine)

# Categories from user's reference
CATEGORIES = [
    {"name": "Industrial Supplies", "description": "Industrial machinery, parts, and equipment", "image_url": "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?w=500&h=500&fit=crop", "id": 1, "slug": "industrial-supplies"},
    {"name": "Textiles", "description": "Fabrics, clothing materials, and textile products", "image_url": "https://images.unsplash.com/photo-1586075010923-2dd4570fb338?w=500&h=500&fit=crop", "id": 2, "slug": "textiles"},
    {"name": "Electronics", "description": "Electronic components, devices, and equipment", "image_url": "https://images.unsplash.com/photo-1518717758536-85ae29035b6d?w=500&h=500&fit=crop", "id": 3, "slug": "electronics"},
    {"name": "Kitchen Equipment", "description": "Commercial and residential kitchen equipment", "image_url": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=500&h=500&fit=crop", "id": 4, "slug": "kitchen-equipment"},
    {"name": "Food & Beverages", "description": "Food ingredients, beverages, and related products", "image_url": "https://images.unsplash.com/photo-1586201375761-83865001e31c?w=500&h=500&fit=crop", "id": 5, "slug": "food-beverages"},
    {"name": "Furniture", "description": "Office and home furniture", "image_url": "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=500&h=500&fit=crop", "id": 6, "slug": "furniture"},
    {"name": "Safety Equipment", "description": "Industrial and personal safety equipment", "image_url": "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=500&h=500&fit=crop", "id": 7, "slug": "safety-equipment"},
    {"name": "Pharmaceuticals", "description": "Pharmaceutical ingredients and products", "image_url": "https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=500&h=500&fit=crop", "id": 8, "slug": "pharmaceuticals"}
]

# Sample products with relevant images (one per category)
SAMPLE_PRODUCTS = [
    {
        "name": "Industrial Hydraulic Pump",
        "category_id": 1,
        "description": "High-performance hydraulic pump for industrial machinery. Suitable for heavy-duty applications with excellent durability and efficiency.",
        "price": 25000.00,
        "stock_quantity": 50,
        "image_urls": [
            "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?w=800&h=600&fit=crop",
            "https://images.unsplash.com/photo-1565043666747-69f6646db940?w=800&h=600&fit=crop"
        ],
        "hsn_code": "8413",
        "tax_rate": 18.0,
        "slug": "industrial-hydraulic-pump"
    },
    {
        "name": "Premium Cotton Fabric",
        "category_id": 2,
        "description": "100% premium cotton fabric, perfect for garment manufacturing. Soft texture with excellent color retention and durability.",
        "price": 450.00,
        "stock_quantity": 200,
        "image_urls": [
            "https://images.unsplash.com/photo-1586075010923-2dd4570fb338?w=800&h=600&fit=crop",
            "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800&h=600&fit=crop"
        ],
        "hsn_code": "5208",
        "tax_rate": 5.0,
        "slug": "premium-cotton-fabric"
    },
    {
        "name": "LED Display Module",
        "category_id": 3,
        "description": "High-resolution LED display module with excellent brightness and color accuracy. Ideal for digital signage and electronic displays.",
        "price": 3500.00,
        "stock_quantity": 75,
        "image_urls": [
            "https://images.unsplash.com/photo-1518717758536-85ae29035b6d?w=800&h=600&fit=crop",
            "https://images.unsplash.com/photo-1563770660941-20978e870e26?w=800&h=600&fit=crop"
        ],
        "hsn_code": "8531",
        "tax_rate": 18.0,
        "slug": "led-display-module"
    },
    {
        "name": "Commercial Mixer Grinder",
        "category_id": 4,
        "description": "Heavy-duty commercial mixer grinder for restaurants and catering services. Powerful motor with multiple speed settings.",
        "price": 15000.00,
        "stock_quantity": 30,
        "image_urls": [
            "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=800&h=600&fit=crop",
            "https://images.unsplash.com/photo-1574781330855-d0db2706b3d0?w=800&h=600&fit=crop"
        ],
        "hsn_code": "8509",
        "tax_rate": 18.0,
        "slug": "commercial-mixer-grinder"
    },
    {
        "name": "Organic Basmati Rice",
        "category_id": 5,
        "description": "Premium quality organic basmati rice, aged for perfect aroma and taste. Ideal for restaurants and bulk buyers.",
        "price": 120.00,
        "stock_quantity": 500,
        "image_urls": [
            "https://images.unsplash.com/photo-1586201375761-83865001e31c?w=800&h=600&fit=crop",
            "https://images.unsplash.com/photo-1596040033229-a9821ebd058d?w=800&h=600&fit=crop"
        ],
        "hsn_code": "1006",
        "tax_rate": 5.0,
        "slug": "organic-basmati-rice"
    },
    {
        "name": "Executive Office Chair",
        "category_id": 6,
        "description": "Ergonomic executive office chair with premium leather upholstery. Adjustable height and lumbar support for maximum comfort.",
        "price": 12000.00,
        "stock_quantity": 25,
        "image_urls": [
            "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=800&h=600&fit=crop",
            "https://images.unsplash.com/photo-1541558869434-2840d308329a?w=800&h=600&fit=crop"
        ],
        "hsn_code": "9401",
        "tax_rate": 18.0,
        "slug": "executive-office-chair"
    },
    {
        "name": "Industrial Safety Helmet",
        "category_id": 7,
        "description": "High-quality industrial safety helmet with adjustable fit. Meets international safety standards for construction and industrial use.",
        "price": 850.00,
        "stock_quantity": 100,
        "image_urls": [
            "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=800&h=600&fit=crop",
            "https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=800&h=600&fit=crop"
        ],
        "hsn_code": "6506",
        "tax_rate": 18.0,
        "slug": "industrial-safety-helmet"
    },
    {
        "name": "Pharmaceutical Grade Vitamin C",
        "category_id": 8,
        "description": "High-purity pharmaceutical grade Vitamin C powder. Suitable for pharmaceutical manufacturing and supplement production.",
        "price": 2500.00,
        "stock_quantity": 60,
        "image_urls": [
            "https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=800&h=600&fit=crop",
            "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=800&h=600&fit=crop"
        ],
        "hsn_code": "2936",
        "tax_rate": 12.0,
        "slug": "pharmaceutical-grade-vitamin-c"
    }
]

def clean_database(db: Session):
    """Remove all existing products and related data"""
    print("Cleaning existing products...")
    
    from sqlalchemy import text
    
    # Delete in order to avoid foreign key constraints
    db.execute(text("DELETE FROM invoice_line_items WHERE product_id IS NOT NULL"))
    db.execute(text("DELETE FROM order_items"))
    db.execute(text("DELETE FROM cart_items"))
    db.execute(text("DELETE FROM product_category"))
    
    # Then delete products
    deleted_products = db.query(models.Product).delete()
    print(f"Deleted {deleted_products} products")
    
    db.commit()

def create_admin_user(db: Session):
    """Create admin user for login"""
    admin_email = "admin@azlok.com"
    admin_username = "admin"
    
    # Check if admin already exists
    existing_admin = db.query(models.User).filter(
        models.User.email == admin_email
    ).first()
    
    if not existing_admin:
        # Hash password "admin123"
        hashed_password = get_password_hash("admin123")
        
        admin = models.User(
            email=admin_email,
            username=admin_username,
            hashed_password=hashed_password,
            full_name="System Administrator",
            phone="+911234567890",
            role=models.UserRole.ADMIN,
            is_active=True,
            business_name="Azlok Enterprises",
            business_address=json.dumps({
                "street": "123 Business Park",
                "city": "Mumbai",
                "state": "Maharashtra",
                "postal_code": "400001",
                "country": "India"
            }),
            region="Mumbai"
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"Created admin user: {admin.email} (password: admin123)")
        return admin
    else:
        print(f"Admin user already exists: {existing_admin.email}")
        return existing_admin

def create_seller_user(db: Session):
    """Create a seller user for products"""
    seller_email = "seller@azlok.com"
    seller_username = "azlok_seller"
    
    # Check if seller already exists
    existing_seller = db.query(models.User).filter(
        (models.User.email == seller_email) | (models.User.username == seller_username)
    ).first()
    
    if not existing_seller:
        # Hash password "seller123"
        hashed_password = get_password_hash("seller123")
        
        seller = models.User(
            email=seller_email,
            username=seller_username,
            hashed_password=hashed_password,
            full_name="Azlok Seller",
            phone="+911234567891",
            role=models.UserRole.SELLER,
            is_active=True,
            business_name="Azlok Trading Co.",
            business_address=json.dumps({
                "street": "456 Trade Center",
                "city": "Mumbai",
                "state": "Maharashtra",
                "postal_code": "400002",
                "country": "India"
            }),
            gst_number="27ABCDE1234F1Z5",
            region="Mumbai"
        )
        
        db.add(seller)
        db.commit()
        db.refresh(seller)
        print(f"Created seller user: {seller.email} (password: seller123)")
        return seller
    else:
        print(f"Seller user already exists: {existing_seller.email}")
        return existing_seller

def update_categories(db: Session):
    """Update categories with proper images"""
    print("Updating categories with images...")
    
    for cat_data in CATEGORIES:
        category = db.query(models.Category).filter(models.Category.id == cat_data["id"]).first()
        if category:
            category.image_url = cat_data["image_url"]
            print(f"Updated category image: {category.name}")
    
    db.commit()

def create_products(db: Session, seller_id: int, admin_id: int):
    """Create sample products"""
    print("Creating sample products...")
    
    for product_data in SAMPLE_PRODUCTS:
        # Generate SKU
        sku = f"AZL{product_data['category_id']:02d}{len(SAMPLE_PRODUCTS):03d}"
        
        product = models.Product(
            name=product_data["name"],
            slug=product_data["slug"],
            sku=sku,
            description=product_data["description"],
            base_price=product_data["price"] * 0.85,  # 15% margin
            price=product_data["price"],
            stock_quantity=product_data["stock_quantity"],
            image_urls=json.dumps(product_data["image_urls"]),
            seller_id=seller_id,
            hsn_code=product_data["hsn_code"],
            tax_rate=product_data["tax_rate"],
            is_tax_inclusive=False,
            gst_details=json.dumps({
                "cgst": product_data["tax_rate"] / 2,
                "sgst": product_data["tax_rate"] / 2,
                "igst": product_data["tax_rate"]
            }),
            approval_status=models.ApprovalStatus.APPROVED,
            approved_by=admin_id
        )
        
        db.add(product)
        db.commit()
        db.refresh(product)
        
        # Add category to product
        category = db.query(models.Category).filter(models.Category.id == product_data["category_id"]).first()
        if category:
            product.categories.append(category)
            db.commit()
        
        print(f"Created product: {product.name} (SKU: {product.sku})")

def main():
    """Main function to clean and seed database"""
    db = SessionLocal()
    
    try:
        print("Starting database cleanup and seeding...")
        
        # Clean existing products
        clean_database(db)
        
        # Create admin user
        admin = create_admin_user(db)
        
        # Create seller user
        seller = create_seller_user(db)
        
        # Update categories with images
        update_categories(db)
        
        # Create sample products
        create_products(db, seller.id, admin.id)
        
        print("\n" + "="*50)
        print("Database seeding completed successfully!")
        print("="*50)
        print("Admin Login:")
        print("  Email: admin@azlok.com")
        print("  Password: admin123")
        print("\nSeller Login:")
        print("  Email: seller@azlok.com")
        print("  Password: seller123")
        print("="*50)
        
    except Exception as e:
        print(f"Error during database seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()

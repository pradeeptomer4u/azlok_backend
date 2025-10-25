from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc, or_, and_
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import logging

from .. import models, schemas
from ..database import get_db
from .auth import get_current_active_user
from ..cache import cached, invalidate_products_cache, invalidate_product_cache, redis_client
from fastapi.encoders import jsonable_encoder

router = APIRouter()

def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from a product name"""
    return name.lower().replace(" ", "-")

def generate_sku(db: Session, name: str) -> str:
    """Generate a unique SKU for a product"""
    # Get the first 3 letters of the name
    prefix = ''.join(c for c in name[:3] if c.isalpha()).upper()
    if not prefix:
        prefix = "PRD"
    
    # Count existing products with this prefix
    count = db.query(models.Product).filter(models.Product.sku.like(f"{prefix}%")).count()
    
    # Generate SKU with prefix and incremented count
    return f"{prefix}{count+1:06d}"

@router.post("/", response_model=schemas.Product)
async def create_product(
    product: schemas.ProductCreate,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Only sellers, admins, and company personnel can create products
    if current_user.role not in [models.UserRole.SELLER, models.UserRole.ADMIN, models.UserRole.COMPANY]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Generate slug if not provided
    if not product.slug:
        product.slug = generate_slug(product.name)
    
    # Check if slug already exists
    existing_product = db.query(models.Product).filter(models.Product.slug == product.slug).first()
    if existing_product:
        raise HTTPException(status_code=400, detail="Product with this slug already exists")
    
    # Generate SKU
    sku = product.sku if hasattr(product, 'sku') and product.sku else generate_sku(db, product.name)
    
    # Check if SKU already exists
    existing_sku = db.query(models.Product).filter(models.Product.sku == sku).first()
    if existing_sku:
        raise HTTPException(status_code=400, detail="Product with this SKU already exists")
    
    # Prepare gst_details with features and specifications
    gst_details = {}
    if product.gst_details:
        gst_details = product.gst_details.dict() if hasattr(product.gst_details, 'dict') else product.gst_details
    
    # Add features and specifications to gst_details
    if product.features:
        gst_details['features'] = product.features
    if product.specifications:
        gst_details['specifications'] = product.specifications
    
    # Create product
    db_product = models.Product(
        name=product.name,
        slug=product.slug,
        sku=sku,
        description=product.description,
        price=product.price,
        base_price=product.base_price,  # Use the provided base_price instead of price
        hsn_code=product.hsn_code,      # Add hsn_code
        tax_rate=product.tax_rate,      # Add tax_rate
        is_tax_inclusive=product.is_tax_inclusive,  # Add is_tax_inclusive
        stock_quantity=product.stock_quantity,
        image_urls=json.dumps(product.image_urls),
        seller_id=current_user.id,
        gst_details=json.dumps(gst_details) if gst_details else None,
        approval_status=models.ApprovalStatus.PENDING if current_user.role == models.UserRole.SELLER else models.ApprovalStatus.APPROVED,
        approved_by=None if current_user.role == models.UserRole.SELLER else current_user.id
    )
    
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    
    # Add categories
    for category_id in product.category_ids:
        category = db.query(models.Category).filter(models.Category.id == category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail=f"Category with id {category_id} not found")
        db_product.categories.append(category)
    
    db.commit()
    db.refresh(db_product)
    
    # Invalidate products cache after creation
    invalidate_products_cache()
    
    # Store product in Redis for faster search
    product_data = {
        "id": db_product.id,
        "name": db_product.name,
        "slug": db_product.slug,
        "sku": db_product.sku,
        "description": db_product.description,
        "price": db_product.price,
        "categories": [c.id for c in db_product.categories]
    }

    return db_product

@router.get("/", response_model=List[schemas.Product])
@cached(expire=300, key_prefix="products")  # Cache for 5 minutes
def read_products(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc",
    approval_status: Optional[models.ApprovalStatus] = None,
    seller_id: Optional[int] = None,
    is_featured: Optional[bool] = None,
    is_bestseller: Optional[bool] = None,
    size: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Product).filter(models.Product.approval_status == models.ApprovalStatus.APPROVED)
    
    # Apply category filter if provided
    if category_id:
        query = query.join(models.Product.categories).filter(models.Category.id == category_id)
    
    # Apply featured filter if provided
    # For now, we'll consider products with higher stock as featured
    # In a real implementation, you might want to add a is_featured column to the Product model
    if is_featured is not None:
        if is_featured:
            # For demonstration, we'll consider products with stock > 10 as featured
            # This is a temporary solution until a proper is_featured field is added
            query = query.filter(models.Product.stock_quantity > 10)
            
    # Apply bestseller filter if provided
    # For now, we'll consider products with highest stock quantity as bestsellers
    if is_bestseller is not None:
        if is_bestseller:
            # For demonstration, we'll consider products with stock > 20 as bestsellers
            query = query.filter(models.Product.stock_quantity > 20)
            # Order by stock quantity descending to get the true bestsellers first
            query = query.order_by(models.Product.stock_quantity.desc())
    
    # Apply sorting if provided
    if sort_by and not is_bestseller:  # Don't override bestseller sorting
        if sort_by == "price":
            if sort_order == "desc":
                query = query.order_by(desc(models.Product.price))
            else:
                query = query.order_by(asc(models.Product.price))
        elif sort_by == "rating":
            if sort_order == "desc":
                query = query.order_by(desc(models.Product.rating))
            else:
                query = query.order_by(asc(models.Product.rating))
        elif sort_by == "name":
            if sort_order == "desc":
                query = query.order_by(desc(models.Product.name))
            else:
                query = query.order_by(asc(models.Product.name))
        elif sort_by == "created_at":
            if sort_order == "desc":
                query = query.order_by(desc(models.Product.created_at))
            else:
                query = query.order_by(asc(models.Product.created_at))
    
    # Use size parameter if provided, otherwise use limit
    if size is not None:
        limit = size
    
    products = query.offset(skip).limit(limit).all()
    
    # Process products to handle JSON fields
    for product in products:
        # Parse image_urls from JSON string to list
        if product.image_urls:
            try:
                product.image_urls = json.loads(product.image_urls)
            except:
                product.image_urls = []
        else:
            product.image_urls = []
            
        # Parse gst_details if present
        if product.gst_details and isinstance(product.gst_details, str):
            try:
                gst_data = json.loads(product.gst_details)
                product.gst_details = gst_data
                
                # Extract features from gst_details
                if 'features' in gst_data:
                    product.features = gst_data['features']
                else:
                    product.features = []
                
                # Extract specifications from gst_details
                if 'specifications' in gst_data:
                    product.specifications = gst_data['specifications']
                else:
                    product.specifications = []
            except:
                product.gst_details = {}
                product.features = []
                product.specifications = []
        else:
            product.features = []
            product.specifications = []
                
        # Handle seller's business_address if present
        if product.seller and product.seller.business_address and isinstance(product.seller.business_address, str):
            try:
                product.seller.business_address = json.loads(product.seller.business_address)
            except:
                product.seller.business_address = {}
        if product.categories:
            product.categories = [jsonable_encoder(category) for category in product.categories]

    return [jsonable_encoder(product) for product in products]


@router.get("/search", response_model=schemas.SearchResults)
async def search_products(
    query: str,
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    tax_inclusive_only: Optional[bool] = None,
    max_tax_rate: Optional[float] = None,
    buyer_state: Optional[str] = None,
    seller_state: str = 'MH',  # Default to Maharashtra
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    # Start with base query for approved products
    db_query = db.query(models.Product).filter(models.Product.approval_status == models.ApprovalStatus.APPROVED)
    
    # Apply search filters
    search_filter = or_(
        models.Product.name.ilike(f"%{query}%"),
        models.Product.description.ilike(f"%{query}%"),
        models.Product.sku.ilike(f"%{query}%")
    )
    db_query = db_query.filter(search_filter)
    
    # Apply category filter if provided
    if category_id:
        db_query = db_query.join(models.Product.categories).filter(models.Category.id == category_id)
    
    # Apply price filters if provided
    if min_price is not None:
        db_query = db_query.filter(models.Product.price >= min_price)
    if max_price is not None:
        db_query = db_query.filter(models.Product.price <= max_price)
        
    # Apply tax-inclusive filter if provided
    if tax_inclusive_only is not None and tax_inclusive_only:
        db_query = db_query.filter(models.Product.is_tax_inclusive == True)
    
    # Get paginated results first
    offset = (page - 1) * limit
    products = db_query.offset(offset).limit(limit).all()
    
    # Apply tax rate filter if provided (requires fetching tax info)
    filtered_products = products
    if max_tax_rate is not None or buyer_state is not None:
        from .tax import calculate_tax
        from .. import schemas
        
        # Process each product for tax information
        products_with_tax = []
        for product in products:
            try:
                # Create tax calculation request
                tax_request = schemas.TaxCalculationRequest(
                    product_id=product.id,
                    quantity=1,
                    buyer_state=buyer_state,
                    seller_state=seller_state
                )
                
                # Calculate tax for the product
                tax_info = await calculate_tax(tax_request, None, db)
                
                # Filter by max tax rate if specified
                if max_tax_rate is not None and tax_info["tax_percentage"] > max_tax_rate:
                    continue
                    
                # Add product to filtered list
                products_with_tax.append(product)
            except Exception as e:
                # Skip products with tax calculation errors
                continue
                
        filtered_products = products_with_tax
    
    # Count total results (approximate if using tax filtering)
    if max_tax_rate is not None or buyer_state is not None:
        total = len(filtered_products)
        # For accurate pagination with tax filtering, we'd need to process all products
        # This is a simplified approach that may not be perfect for large datasets
    else:
        total = db_query.count()
    
    # Calculate pagination
    total_pages = (total + limit - 1) // limit  # Ceiling division
    
    return {
        "results": filtered_products,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": total_pages
    }

@router.get("/{product_id}", response_model=schemas.Product)
@cached(expire=600, key_prefix="products")  # Cache for 10 minutes
async def read_product(product_id: int, db: Session = Depends(get_db)):
    # Invalidate the cache for this product to ensure we get fresh data
    invalidate_product_cache(product_id)
    
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # If product is not approved, only seller, admins, and company personnel can view it
    if product.approval_status != models.ApprovalStatus.APPROVED:
        current_user = await get_current_active_user()
        if current_user.id != product.seller_id and current_user.role not in [models.UserRole.ADMIN, models.UserRole.COMPANY]:
            raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Parse image_urls from JSON string to list
    if product.image_urls:
        try:
            product.image_urls = json.loads(product.image_urls)
        except:
            product.image_urls = []
    else:
        product.image_urls = []
        
    # Parse gst_details if present
    if product.gst_details and isinstance(product.gst_details, str):
        try:
            gst_data = json.loads(product.gst_details)
            product.gst_details = gst_data
            
            # Extract features from gst_details
            if 'features' in gst_data:
                product.features = gst_data['features']
            
            # Extract specifications from gst_details
            if 'specifications' in gst_data:
                product.specifications = gst_data['specifications']
        except:
            product.gst_details = {}
            product.features = []
            product.specifications = []
    else:
        product.features = []
        product.specifications = []
            
    # Handle seller's business_address if present
    if product.seller and product.seller.business_address and isinstance(product.seller.business_address, str):
        try:
            product.seller.business_address = json.loads(product.seller.business_address)
        except:
            product.seller.business_address = {}
    
    return jsonable_encoder(product)

@router.put("/{product_id}", response_model=schemas.Product)
async def update_product(
    product_id: int,
    product_update: schemas.ProductUpdate,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Only the seller, admins, and company personnel can update the product
    if db_product.seller_id != current_user.id and current_user.role not in [models.UserRole.ADMIN, models.UserRole.COMPANY]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Update product fields if provided
    if product_update.name is not None:
        db_product.name = product_update.name
    
    if product_update.description is not None:
        db_product.description = product_update.description
    
    if product_update.price is not None:
        db_product.price = product_update.price
    
    if product_update.base_price is not None:
        db_product.base_price = product_update.base_price
    
    if product_update.hsn_code is not None:
        db_product.hsn_code = product_update.hsn_code
    
    if product_update.tax_rate is not None:
        db_product.tax_rate = product_update.tax_rate
    
    if product_update.is_tax_inclusive is not None:
        db_product.is_tax_inclusive = product_update.is_tax_inclusive
    
    if product_update.stock_quantity is not None:
        db_product.stock_quantity = product_update.stock_quantity
    
    if product_update.image_urls is not None:
        # Store as JSON string but ensure it's properly serialized
        db_product.image_urls = json.dumps(product_update.image_urls)
    
    # Initialize gst_details if it doesn't exist
    if db_product.gst_details is None:
        db_product.gst_details = {}
    elif isinstance(db_product.gst_details, str):
        try:
            db_product.gst_details = json.loads(db_product.gst_details)
        except json.JSONDecodeError:
            db_product.gst_details = {}
            
    # Update GST details if provided
    if product_update.gst_details is not None:
        gst_data = product_update.gst_details.dict() if hasattr(product_update.gst_details, 'dict') else product_update.gst_details
        if isinstance(db_product.gst_details, dict):
            db_product.gst_details.update(gst_data)
        else:
            db_product.gst_details = gst_data
            
    # Store features in gst_details if provided
    if product_update.features is not None:
        if isinstance(db_product.gst_details, dict):
            db_product.gst_details['features'] = product_update.features
        else:
            db_product.gst_details = {'features': product_update.features}
            
    # Store specifications in gst_details if provided
    if product_update.specifications is not None:
        if isinstance(db_product.gst_details, dict):
            db_product.gst_details['specifications'] = product_update.specifications
        else:
            db_product.gst_details = {'specifications': product_update.specifications}
            
    # Ensure gst_details is stored as JSON
    if isinstance(db_product.gst_details, dict):
        db_product.gst_details = json.dumps(db_product.gst_details)
    
    # Only admins and company personnel can update approval status
    if product_update.approval_status is not None and current_user.role in [models.UserRole.ADMIN, models.UserRole.COMPANY]:
        db_product.approval_status = product_update.approval_status
        if product_update.approval_status != models.ApprovalStatus.PENDING:
            db_product.approved_by = current_user.id
    
    # Update categories if provided
    if product_update.category_ids is not None:
        # Clear existing categories
        db_product.categories = []
        
        # Add new categories
        for category_id in product_update.category_ids:
            category = db.query(models.Category).filter(models.Category.id == category_id).first()
            if not category:
                raise HTTPException(status_code=404, detail=f"Category with id {category_id} not found")
            db_product.categories.append(category)
    
    db.commit()
    db.refresh(db_product)
    
    # Update product in Redis
    product_data = {
    "id": db_product.id,
    "name": db_product.name,
    "slug": db_product.slug,
    "sku": db_product.sku,
    "description": db_product.description,
    "price": db_product.price,
    "base_price": db_product.base_price,
    "hsn_code": db_product.hsn_code,
    "tax_rate": db_product.tax_rate,
    "is_tax_inclusive": db_product.is_tax_inclusive,
    "categories": [c.id for c in db_product.categories]
    }
    
    # Safely update Redis if available
    # if redis_client is not None:
    #     try:
    #         redis_client.hset(f"product:{db_product.id}", mapping=product_data)
    #     except Exception as e:
    #         # Log error but continue - Redis is optional
    #         logging.warning(f"Failed to update product in Redis: {e}")
    
    return db_product

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Only the seller, admins, and company personnel can delete the product
    if db_product.seller_id != current_user.id and current_user.role not in [models.UserRole.ADMIN, models.UserRole.COMPANY]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Delete product from Redis
    if redis_client is not None:
        try:
            redis_client.delete(f"product:{db_product.id}")
        except Exception as e:
            # Log error but continue - Redis is optional
            logging.warning(f"Failed to delete product from Redis: {e}")
    
    # Delete product from database
    db.delete(db_product)
    db.commit()
    
    return {"status": "success"}

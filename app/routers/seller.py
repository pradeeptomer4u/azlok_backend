from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
from typing import List, Optional
import json
import re
import uuid
from datetime import datetime, timedelta

from .. import models, schemas
from ..database import get_db
from .auth import get_current_active_user
from ..utils.r2_storage import r2_storage
from ..utils.email_service import EmailService

router = APIRouter()

# Helper function to create URL-friendly slugs
def slugify(text):
    # Convert to lowercase and remove non-alphanumeric characters
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    # Replace spaces with hyphens
    text = re.sub(r'[\s]+', '-', text)
    # Remove consecutive hyphens
    text = re.sub(r'-+', '-', text)
    # Remove leading/trailing hyphens
    text = text.strip('-')
    return text

# Helper function to check seller permissions
async def get_seller_user(current_user: schemas.User = Depends(get_current_active_user)):
    if current_user.role != models.UserRole.SELLER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can access this endpoint"
        )
    return current_user

# Seller dashboard
@router.get("/dashboard", response_model=dict)
async def seller_dashboard(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: schemas.User = Depends(get_seller_user),
    db: Session = Depends(get_db)
):
    # Parse date range or use default (last 30 days)
    try:
        if start_date:
            start = datetime.fromisoformat(start_date)
        else:
            start = datetime.now() - timedelta(days=30)
            
        if end_date:
            end = datetime.fromisoformat(end_date)
        else:
            end = datetime.now()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use ISO format (YYYY-MM-DD)."
        )
    
    # Get counts for dashboard
    total_products = db.query(models.Product).filter(
        models.Product.seller_id == current_user.id
    ).count()
    
    pending_approval = db.query(models.Product).filter(
        models.Product.seller_id == current_user.id,
        models.Product.approval_status == models.ApprovalStatus.PENDING
    ).count()
    
    # Get order statistics
    total_orders = db.query(models.OrderItem).filter(
        models.OrderItem.seller_id == current_user.id,
        models.OrderItem.created_at.between(start, end)
    ).count()
    
    # Calculate total sales
    sales_result = db.query(func.sum(models.OrderItem.total)).filter(
        models.OrderItem.seller_id == current_user.id,
        models.OrderItem.created_at.between(start, end)
    ).scalar()
    
    total_sales = float(sales_result) if sales_result else 0
    
    # Get recent orders
    recent_orders_query = db.query(models.Order).join(
        models.OrderItem, models.Order.id == models.OrderItem.order_id
    ).filter(
        models.OrderItem.seller_id == current_user.id
    ).order_by(
        desc(models.Order.created_at)
    ).limit(5).all()
    
    recent_orders = []
    for order in recent_orders_query:
        # Get order items for this seller only
        items = db.query(models.OrderItem).filter(
            models.OrderItem.order_id == order.id,
            models.OrderItem.seller_id == current_user.id
        ).all()
        
        # Get customer info
        customer = db.query(models.User).filter(
            models.User.id == order.user_id
        ).first()
        
        recent_orders.append({
            "id": order.id,
            "order_number": order.order_number,
            "date": order.created_at,
            "customer_name": customer.full_name if customer else "Unknown",
            "status": order.status,
            "payment_status": order.payment_status,
            "total": sum(item.total for item in items)
        })
    
    # Get top products
    top_products_query = db.query(
        models.Product,
        func.sum(models.OrderItem.quantity).label("total_sold"),
        func.sum(models.OrderItem.total).label("total_revenue")
    ).join(
        models.OrderItem, models.Product.id == models.OrderItem.product_id
    ).filter(
        models.Product.seller_id == current_user.id,
        models.OrderItem.created_at.between(start, end)
    ).group_by(
        models.Product.id
    ).order_by(
        desc("total_revenue")
    ).limit(5).all()
    
    top_products = []
    for product, total_sold, total_revenue in top_products_query:
        top_products.append({
            "id": product.id,
            "name": product.name,
            "sku": product.sku,
            "image": json.loads(product.image_urls)[0] if product.image_urls else None,
            "total_sold": total_sold,
            "total_revenue": total_revenue
        })
    
    # Get sales data for chart
    sales_data = []
    for i in range((end - start).days + 1):
        day = start + timedelta(days=i)
        next_day = day + timedelta(days=1)
        
        daily_sales = db.query(func.sum(models.OrderItem.total)).filter(
            models.OrderItem.seller_id == current_user.id,
            models.OrderItem.created_at.between(day, next_day)
        ).scalar()
        
        sales_data.append({
            "date": day.strftime("%Y-%m-%d"),
            "amount": float(daily_sales) if daily_sales else 0
        })
    
    return {
        "total_products": total_products,
        "pending_approval": pending_approval,
        "total_orders": total_orders,
        "total_sales": total_sales,
        "recent_orders": recent_orders,
        "top_products": top_products,
        "sales_data": sales_data
    }

# Seller products
@router.get("/products", response_model=schemas.SearchResults)
async def get_seller_products(
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    status: Optional[models.ApprovalStatus] = None,
    sort_by: Optional[str] = None,
    sort_desc: bool = False,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: schemas.User = Depends(get_seller_user),
    db: Session = Depends(get_db)
):
    # Base query
    query = db.query(models.Product).filter(models.Product.seller_id == current_user.id)
    
    # Apply filters
    if search:
        query = query.filter(
            (models.Product.name.ilike(f"%{search}%")) | 
            (models.Product.sku.ilike(f"%{search}%")) |
            (models.Product.description.ilike(f"%{search}%"))
        )
    
    if category_id:
        query = query.join(models.product_category).filter(
            models.product_category.c.category_id == category_id
        )
    
    if status:
        query = query.filter(models.Product.approval_status == status)
    
    # Count total before pagination
    total = query.count()
    
    # Apply sorting
    if sort_by:
        if sort_by == "name":
            query = query.order_by(desc(models.Product.name) if sort_desc else asc(models.Product.name))
        elif sort_by == "price":
            query = query.order_by(desc(models.Product.price) if sort_desc else asc(models.Product.price))
        elif sort_by == "stock":
            query = query.order_by(desc(models.Product.stock_quantity) if sort_desc else asc(models.Product.stock_quantity))
        elif sort_by == "created_at":
            query = query.order_by(desc(models.Product.created_at) if sort_desc else asc(models.Product.created_at))
    else:
        # Default sort by created_at desc
        query = query.order_by(desc(models.Product.created_at))
    
    # Apply pagination
    query = query.offset((page - 1) * limit).limit(limit)
    
    # Execute query
    products = query.all()
    
    # Calculate total pages
    pages = (total + limit - 1) // limit
    
    return {
        "results": products,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages
    }

# Get product by ID
@router.get("/products/{product_id}", response_model=schemas.Product)
async def get_seller_product(
    product_id: int,
    current_user: schemas.User = Depends(get_seller_user),
    db: Session = Depends(get_db)
):
    product = db.query(models.Product).filter(
        models.Product.id == product_id,
        models.Product.seller_id == current_user.id
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product

# Create product
@router.post("/products", response_model=schemas.Product, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: schemas.ProductCreate,
    current_user: schemas.User = Depends(get_seller_user),
    db: Session = Depends(get_db)
):
    # Convert image_urls list to JSON string
    image_urls_json = json.dumps(product.image_urls)
    
    # Create product
    db_product = models.Product(
        name=product.name,
        slug=product.slug if product.slug else product.name.lower().replace(" ", "-"),
        sku=product.sku,
        description=product.description,
        price=product.price,
        stock_quantity=product.stock_quantity,
        image_urls=image_urls_json,
        seller_id=current_user.id,
        approval_status=models.ApprovalStatus.PENDING
    )
    
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    
    # Add categories
    for category_id in product.category_ids:
        category = db.query(models.Category).filter(models.Category.id == category_id).first()
        if category:
            db_product.categories.append(category)
    
    db.commit()
    db.refresh(db_product)
    
    return db_product

# Update product
@router.put("/products/{product_id}", response_model=schemas.Product)
async def update_product(
    product_id: int,
    product_update: schemas.ProductUpdate,
    current_user: schemas.User = Depends(get_seller_user),
    db: Session = Depends(get_db)
):
    # Get product
    db_product = db.query(models.Product).filter(
        models.Product.id == product_id,
        models.Product.seller_id == current_user.id
    ).first()
    
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Update fields if provided
    if product_update.name is not None:
        db_product.name = product_update.name
    
    if product_update.description is not None:
        db_product.description = product_update.description
    
    if product_update.price is not None:
        db_product.price = product_update.price
    
    if product_update.stock_quantity is not None:
        db_product.stock_quantity = product_update.stock_quantity
    
    if product_update.image_urls is not None:
        db_product.image_urls = json.dumps(product_update.image_urls)
    
    # Reset approval status when product is updated
    db_product.approval_status = models.ApprovalStatus.PENDING
    
    # Update categories if provided
    if product_update.category_ids is not None:
        # Clear existing categories
        db_product.categories = []
        
        # Add new categories
        for category_id in product_update.category_ids:
            category = db.query(models.Category).filter(models.Category.id == category_id).first()
            if category:
                db_product.categories.append(category)
    
    db.commit()
    db.refresh(db_product)
    
    return db_product

# Delete product
@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    current_user: schemas.User = Depends(get_seller_user),
    db: Session = Depends(get_db)
):
    # Get product
    db_product = db.query(models.Product).filter(
        models.Product.id == product_id,
        models.Product.seller_id == current_user.id
    ).first()
    
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if product has orders
    order_items = db.query(models.OrderItem).filter(
        models.OrderItem.product_id == product_id
    ).first()
    
    if order_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete product with existing orders"
        )
    
    # Delete product
    db.delete(db_product)
    db.commit()
    
    return None

# Seller orders
@router.get("/orders", response_model=List[schemas.Order])
async def get_seller_orders(
    status: Optional[models.OrderStatus] = None,
    payment_status: Optional[models.PaymentStatus] = None,
    search: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_desc: bool = False,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: schemas.User = Depends(get_seller_user),
    db: Session = Depends(get_db)
):
    # Get order IDs where this seller has items
    seller_order_ids = db.query(models.OrderItem.order_id).filter(
        models.OrderItem.seller_id == current_user.id
    ).distinct()
    
    # Base query
    query = db.query(models.Order).filter(models.Order.id.in_(seller_order_ids))
    
    # Apply filters
    if status:
        query = query.filter(models.Order.status == status)
    
    if payment_status:
        query = query.filter(models.Order.payment_status == payment_status)
    
    if search:
        query = query.filter(
            (models.Order.order_number.ilike(f"%{search}%"))
        )
    
    # Parse date range
    try:
        if start_date:
            start = datetime.fromisoformat(start_date)
            query = query.filter(models.Order.created_at >= start)
            
        if end_date:
            end = datetime.fromisoformat(end_date)
            query = query.filter(models.Order.created_at <= end)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use ISO format (YYYY-MM-DD)."
        )
    
    # Count total before pagination
    total = query.count()
    
    # Apply sorting
    if sort_by:
        if sort_by == "date":
            query = query.order_by(desc(models.Order.created_at) if sort_desc else asc(models.Order.created_at))
        elif sort_by == "total":
            query = query.order_by(desc(models.Order.total_amount) if sort_desc else asc(models.Order.total_amount))
        elif sort_by == "status":
            query = query.order_by(desc(models.Order.status) if sort_desc else asc(models.Order.status))
    else:
        # Default sort by created_at desc
        query = query.order_by(desc(models.Order.created_at))
    
    # Apply pagination
    query = query.offset((page - 1) * limit).limit(limit)
    
    # Execute query
    orders = query.all()
    
    # For each order, filter items to only include this seller's items
    for order in orders:
        order.items = [item for item in order.items if item.seller_id == current_user.id]
    
    return orders

# Get order by ID
@router.get("/orders/{order_id}", response_model=schemas.Order)
async def get_seller_order(
    order_id: int,
    current_user: schemas.User = Depends(get_seller_user),
    db: Session = Depends(get_db)
):
    # Check if seller has items in this order
    seller_has_items = db.query(models.OrderItem).filter(
        models.OrderItem.order_id == order_id,
        models.OrderItem.seller_id == current_user.id
    ).first()
    
    if not seller_has_items:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Get order
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Filter items to only include this seller's items
    order.items = [item for item in order.items if item.seller_id == current_user.id]
    
    return order

# Update order status
@router.put("/orders/{order_id}/status", response_model=schemas.Order)
async def update_order_status(
    order_id: int,
    status_update: schemas.OrderUpdate,
    background_tasks: BackgroundTasks,
    current_user: schemas.User = Depends(get_seller_user),
    db: Session = Depends(get_db)
):
    # Check if seller has items in this order
    seller_has_items = db.query(models.OrderItem).filter(
        models.OrderItem.order_id == order_id,
        models.OrderItem.seller_id == current_user.id
    ).first()
    
    if not seller_has_items:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Get order
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Update status if provided
    if status_update.status is not None:
        order.status = status_update.status
    
    # Update tracking number if provided
    if status_update.tracking_number is not None:
        order.tracking_number = status_update.tracking_number
    
    # Update notes if provided
    if status_update.notes is not None:
        order.notes = status_update.notes
    
    # Create order status history entry
    status_history = models.OrderStatusHistory(
        order_id=order.id,
        status=status_update.status if status_update.status else order.status,
        notes=status_update.notes,
        created_by=current_user.id
    )
    db.add(status_history)
    db.commit()
    db.refresh(order)
    
    # Send email notification to customer about status update
    if status_update.status:
        # Get customer information
        customer = db.query(models.User).filter(models.User.id == order.user_id).first()
        
        if customer and customer.email:
            # Get all order items for email
            order_items = db.query(models.OrderItem).filter(
                models.OrderItem.order_id == order.id
            ).all()
            
            # Format items for email
            items_for_email = [
                {
                    "product_name": item.product_name,
                    "quantity": item.quantity,
                    "price": item.price
                } for item in order_items
            ]
            
            # Send email notification
            await EmailService.send_order_status_update(
                background_tasks=background_tasks,
                order_id=str(order.id),
                order_number=order.order_number,
                customer_email=customer.email,
                status=order.status,
                items=items_for_email,
                total=order.total_amount
            )
    
    # Filter items to only include this seller's items
    order.items = [item for item in order.items if item.seller_id == current_user.id]
    
    return order

# Product Management Endpoints

# Get seller products with pagination and filtering
@router.get("/products", response_model=schemas.SellerProductListResponse)
async def get_seller_products(
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    approval_status: Optional[schemas.ApprovalStatus] = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    sort_by: Optional[str] = None,
    sort_desc: bool = False,
    current_user: schemas.User = Depends(get_seller_user),
    db: Session = Depends(get_db)
):
    # Base query for seller's products
    query = db.query(models.Product).filter(models.Product.seller_id == current_user.id)
    
    # Apply filters
    if search:
        query = query.filter(
            models.Product.name.ilike(f"%{search}%") | 
            models.Product.description.ilike(f"%{search}%") |
            models.Product.sku.ilike(f"%{search}%")
        )
    
    if category_id:
        query = query.join(models.product_category).filter(
            models.product_category.c.category_id == category_id
        )
    
    if approval_status:
        query = query.filter(models.Product.approval_status == approval_status)
    
    # Get total count
    total = query.count()
    
    # Apply sorting
    if sort_by:
        sort_column = getattr(models.Product, sort_by, None)
        if sort_column:
            query = query.order_by(desc(sort_column) if sort_desc else asc(sort_column))
    else:
        # Default sort by created_at desc
        query = query.order_by(desc(models.Product.created_at))
    
    # Apply pagination
    query = query.offset((page - 1) * size).limit(size)
    
    # Execute query
    products = query.all()
    
    # Calculate total pages
    pages = (total + size - 1) // size
    
    return {
        "products": products,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages
    }

# Get a specific product by ID
@router.get("/products/{product_id}", response_model=schemas.Product)
async def get_seller_product(
    product_id: int,
    current_user: schemas.User = Depends(get_seller_user),
    db: Session = Depends(get_db)
):
    product = db.query(models.Product).filter(
        models.Product.id == product_id,
        models.Product.seller_id == current_user.id
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product

# Create a new product
@router.post("/products", response_model=schemas.Product, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: schemas.ProductCreate,
    current_user: schemas.User = Depends(get_seller_user),
    db: Session = Depends(get_db)
):
    # Generate slug if not provided
    if not product.slug:
        product.slug = f"{slugify(product.name)}-{uuid.uuid4().hex[:8]}"
    else:
        product.slug = slugify(product.slug)
    
    # Check if slug already exists
    existing_product = db.query(models.Product).filter(models.Product.slug == product.slug).first()
    if existing_product:
        product.slug = f"{product.slug}-{uuid.uuid4().hex[:8]}"
    
    # Create new product
    db_product = models.Product(
        name=product.name,
        description=product.description,
        price=product.price,
        stock_quantity=product.stock_quantity,
        image_urls=product.image_urls,
        sku=product.sku,
        slug=product.slug,
        seller_id=current_user.id,
        approval_status=models.ApprovalStatus.PENDING
    )
    
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    
    # Add categories
    for category_id in product.category_ids:
        category = db.query(models.Category).filter(models.Category.id == category_id).first()
        if category:
            db_product.categories.append(category)
    
    db.commit()
    db.refresh(db_product)
    
    return db_product

# Update an existing product
@router.put("/products/{product_id}", response_model=schemas.Product)
async def update_product(
    product_id: int,
    product_update: schemas.ProductUpdate,
    current_user: schemas.User = Depends(get_seller_user),
    db: Session = Depends(get_db)
):
    # Get product
    db_product = db.query(models.Product).filter(
        models.Product.id == product_id,
        models.Product.seller_id == current_user.id
    ).first()
    
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Update product fields
    update_data = product_update.dict(exclude_unset=True)
    
    # Handle category IDs separately
    category_ids = update_data.pop("category_ids", None)
    
    # Update product fields
    for key, value in update_data.items():
        setattr(db_product, key, value)
    
    # Update categories if provided
    if category_ids is not None:
        # Clear existing categories
        db_product.categories = []
        
        # Add new categories
        for category_id in category_ids:
            category = db.query(models.Category).filter(models.Category.id == category_id).first()
            if category:
                db_product.categories.append(category)
    
    # Update timestamp
    db_product.updated_at = datetime.utcnow()
    
    # If product was rejected and is being updated, set back to pending
    if db_product.approval_status == models.ApprovalStatus.REJECTED:
        db_product.approval_status = models.ApprovalStatus.PENDING
    
    db.commit()
    db.refresh(db_product)
    
    return db_product

# Delete a product
@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    current_user: schemas.User = Depends(get_seller_user),
    db: Session = Depends(get_db)
):
    # Get product
    db_product = db.query(models.Product).filter(
        models.Product.id == product_id,
        models.Product.seller_id == current_user.id
    ).first()
    
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if product can be deleted (not in any orders)
    order_items = db.query(models.OrderItem).filter(models.OrderItem.product_id == product_id).first()
    if order_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete product that has been ordered. Consider marking it as inactive instead."
        )
    
    # Delete product
    db.delete(db_product)
    db.commit()
    
    return None

# Get top sellers
@router.get("/top", response_model=List[schemas.Seller])
async def get_top_sellers(
    size: int = Query(4, ge=1, le=10),
    db: Session = Depends(get_db)
):
    """
    Get top sellers based on rating and sales
    """
    # Get sellers ordered by rating
    sellers = db.query(models.Seller).order_by(models.Seller.rating.desc()).limit(size).all()
    
    # If not enough sellers, return what we have
    if len(sellers) < size:
        return sellers
    
    return sellers

# Get seller statistics and analytics
@router.get("/statistics", response_model=dict)
async def get_seller_statistics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: schemas.User = Depends(get_seller_user),
    db: Session = Depends(get_db)
):
    # Parse date range or use default (last 30 days)
    try:
        if start_date:
            start = datetime.fromisoformat(start_date)
        else:
            start = datetime.now() - timedelta(days=30)
            
        if end_date:
            end = datetime.fromisoformat(end_date)
        else:
            end = datetime.now()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use ISO format (YYYY-MM-DD)."
        )
    
    # Get total sales
    sales_result = db.query(func.sum(models.OrderItem.total)).filter(
        models.OrderItem.seller_id == current_user.id,
        models.OrderItem.created_at.between(start, end)
    ).scalar()
    
    total_sales = float(sales_result) if sales_result else 0
    
    # Get total orders
    total_orders = db.query(func.count(models.OrderItem.order_id.distinct())).filter(
        models.OrderItem.seller_id == current_user.id,
        models.OrderItem.created_at.between(start, end)
    ).scalar()
    
    # Get total products sold
    total_products_sold = db.query(func.sum(models.OrderItem.quantity)).filter(
        models.OrderItem.seller_id == current_user.id,
        models.OrderItem.created_at.between(start, end)
    ).scalar()
    
    total_products_sold = int(total_products_sold) if total_products_sold else 0
    
    # Get average order value
    avg_order_value = total_sales / total_orders if total_orders > 0 else 0
    
    # Get sales by category
    sales_by_category = []
    categories = db.query(models.Category).all()
    
    for category in categories:
        category_sales = db.query(func.sum(models.OrderItem.total)).join(
            models.Product, models.OrderItem.product_id == models.Product.id
        ).join(
            models.product_category, models.Product.id == models.product_category.c.product_id
        ).filter(
            models.OrderItem.seller_id == current_user.id,
            models.OrderItem.created_at.between(start, end),
            models.product_category.c.category_id == category.id
        ).scalar()
        
        if category_sales:
            sales_by_category.append({
                "category_id": category.id,
                "category_name": category.name,
                "total_sales": float(category_sales)
            })
    
    # Sort by total sales desc
    sales_by_category.sort(key=lambda x: x["total_sales"], reverse=True)
    
    # Get top selling products
    top_products = db.query(
        models.Product,
        func.sum(models.OrderItem.quantity).label('total_quantity'),
        func.sum(models.OrderItem.total).label('total_sales')
    ).join(
        models.OrderItem, models.Product.id == models.OrderItem.product_id
    ).filter(
        models.OrderItem.seller_id == current_user.id,
        models.OrderItem.created_at.between(start, end)
    ).group_by(
        models.Product.id
    ).order_by(
        desc('total_sales')
    ).limit(5).all()
    
    top_products_data = [{
        "product_id": product.id,
        "product_name": product.name,
        "total_quantity": int(total_quantity),
        "total_sales": float(total_sales)
    } for product, total_quantity, total_sales in top_products]
    
    # Get sales by status
    sales_by_status = db.query(
        models.Order.status,
        func.count(models.OrderItem.order_id.distinct()).label('order_count'),
        func.sum(models.OrderItem.total).label('total_sales')
    ).join(
        models.OrderItem, models.Order.id == models.OrderItem.order_id
    ).filter(
        models.OrderItem.seller_id == current_user.id,
        models.OrderItem.created_at.between(start, end)
    ).group_by(
        models.Order.status
    ).all()
    
    status_data = [{
        "status": status,
        "order_count": int(order_count),
        "total_sales": float(total_sales) if total_sales else 0
    } for status, order_count, total_sales in sales_by_status]
    
    # Get daily sales for the period
    daily_sales = []
    current_date = start.date()
    end_date = end.date()
    
    while current_date <= end_date:
        day_start = datetime.combine(current_date, datetime.min.time())
        day_end = datetime.combine(current_date, datetime.max.time())
        
        # Get sales for this day
        day_sales = db.query(func.sum(models.OrderItem.total)).filter(
            models.OrderItem.seller_id == current_user.id,
            models.OrderItem.created_at.between(day_start, day_end)
        ).scalar()
        
        # Get orders for this day
        day_orders = db.query(func.count(models.OrderItem.order_id.distinct())).filter(
            models.OrderItem.seller_id == current_user.id,
            models.OrderItem.created_at.between(day_start, day_end)
        ).scalar()
        
        daily_sales.append({
            "date": current_date.isoformat(),
            "sales": float(day_sales) if day_sales else 0,
            "orders": int(day_orders) if day_orders else 0
        })
        
        current_date += timedelta(days=1)
    
    # Get inventory status
    low_stock_products = db.query(models.Product).filter(
        models.Product.seller_id == current_user.id,
        models.Product.stock_quantity <= 5,
        models.Product.stock_quantity > 0
    ).order_by(models.Product.stock_quantity).limit(5).all()
    
    low_stock_data = [{
        "product_id": product.id,
        "product_name": product.name,
        "stock_quantity": product.stock_quantity
    } for product in low_stock_products]
    
    out_of_stock_count = db.query(func.count()).filter(
        models.Product.seller_id == current_user.id,
        models.Product.stock_quantity == 0
    ).scalar()
    
    return {
        "total_sales": total_sales,
        "total_orders": total_orders,
        "total_products_sold": total_products_sold,
        "avg_order_value": avg_order_value,
        "sales_by_category": sales_by_category,
        "top_products": top_products_data,
        "sales_by_status": status_data,
        "daily_sales": daily_sales,
        "inventory": {
            "low_stock": low_stock_data,
            "out_of_stock_count": out_of_stock_count
        }
    }

# Upload image to R2 storage
@router.post("/upload/image", response_model=schemas.FileUploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    folder: str = Form("products"),
    current_user: schemas.User = Depends(get_seller_user)
):
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(allowed_types)}"
        )
    
    # Validate file size (max 5MB)
    max_size = 5 * 1024 * 1024  # 5MB
    file_size = 0
    contents = await file.read(max_size + 1)
    file_size = len(contents)
    
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size too large. Max size: 5MB"
        )
    
    # Reset file pointer
    await file.seek(0)
    
    try:
        # Upload file to R2
        result = await r2_storage.upload_file(file, folder=f"{folder}/{current_user.id}")
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )

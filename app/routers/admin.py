from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
from typing import List, Optional
from datetime import datetime

from .. import models, schemas
from ..database import get_db
from .auth import get_current_active_user
from ..utils.email_service import EmailService

router = APIRouter()

# Helper function to check admin permissions
async def get_admin_user(current_user: schemas.User = Depends(get_current_active_user)):
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.COMPANY]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin and company personnel can access this endpoint"
        )
    return current_user

@router.get("/dashboard", response_model=dict)
async def admin_dashboard(
    current_user: schemas.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    # Get counts for dashboard
    total_products = db.query(models.Product).count()
    pending_products = db.query(models.Product).filter(models.Product.approval_status == models.ApprovalStatus.PENDING).count()
    total_categories = db.query(models.Category).count()
    total_users = db.query(models.User).count()
    
    # Count users by role
    buyers = db.query(models.User).filter(models.User.role == models.UserRole.BUYER).count()
    sellers = db.query(models.User).filter(models.User.role == models.UserRole.SELLER).count()
    admins = db.query(models.User).filter(models.User.role == models.UserRole.ADMIN).count()
    company_users = db.query(models.User).filter(models.User.role == models.UserRole.COMPANY).count()
    
    return {
        "total_products": total_products,
        "pending_products": pending_products,
        "total_categories": total_categories,
        "total_users": total_users,
        "user_stats": {
            "buyers": buyers,
            "sellers": sellers,
            "admins": admins,
            "company": company_users
        }
    }

@router.get("/products/pending", response_model=schemas.ProductApprovalListResponse)
async def get_pending_products(
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    seller_id: Optional[int] = None,
    page: int = 1,
    size: int = 10,
    sort_by: Optional[str] = None,
    sort_desc: bool = False,
    current_user: schemas.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    # Base query for pending products
    query = db.query(models.Product).filter(
        models.Product.approval_status == models.ApprovalStatus.PENDING
    )
    
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
    
    if seller_id:
        query = query.filter(models.Product.seller_id == seller_id)
    
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

@router.put("/products/{product_id}/approve", response_model=schemas.ProductApprovalResponse)
async def approve_product(
    product_id: int,
    background_tasks: BackgroundTasks,
    current_user: schemas.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    # Get product
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get seller information
    seller = db.query(models.User).filter(models.User.id == product.seller_id).first()
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    
    # Update approval status
    product.approval_status = models.ApprovalStatus.APPROVED
    product.approved_by = current_user.id
    product.approval_date = datetime.utcnow()
    
    db.commit()
    db.refresh(product)
    
    # Send email notification to seller
    if seller.email:
        email_service = EmailService()
        background_tasks.add_task(
            email_service.send_email,
            recipient_email=seller.email,
            subject="Your Product Has Been Approved",
            template_name="product_approved.html",
            template_data={
                "seller_name": seller.full_name,
                "product_name": product.name,
                "product_id": product.id,
                "approval_date": product.approval_date.strftime("%Y-%m-%d %H:%M:%S"),
                "admin_name": current_user.full_name
            }
        )
    
    return {
        "product_id": product.id,
        "product_name": product.name,
        "seller_id": seller.id,
        "seller_name": seller.full_name,
        "status": product.approval_status,
        "rejection_reason": None,
        "updated_at": product.approval_date
    }

@router.put("/products/{product_id}/reject", response_model=schemas.ProductApprovalResponse)
async def reject_product(
    product_id: int,
    approval_request: schemas.ProductApprovalRequest,
    background_tasks: BackgroundTasks,
    current_user: schemas.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    # Get product
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Validate rejection status
    if approval_request.status != models.ApprovalStatus.REJECTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status for rejection endpoint"
        )
    
    # Ensure rejection reason is provided
    if not approval_request.rejection_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rejection reason is required"
        )
    
    # Get seller information
    seller = db.query(models.User).filter(models.User.id == product.seller_id).first()
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    
    # Update approval status
    product.approval_status = models.ApprovalStatus.REJECTED
    product.approved_by = current_user.id
    product.approval_date = datetime.utcnow()
    product.rejection_reason = approval_request.rejection_reason
    
    db.commit()
    db.refresh(product)
    
    # Send email notification to seller
    if seller.email:
        email_service = EmailService()
        background_tasks.add_task(
            email_service.send_email,
            recipient_email=seller.email,
            subject="Your Product Requires Updates",
            template_name="product_rejected.html",
            template_data={
                "seller_name": seller.full_name,
                "product_name": product.name,
                "product_id": product.id,
                "rejection_reason": product.rejection_reason,
                "rejection_date": product.approval_date.strftime("%Y-%m-%d %H:%M:%S"),
                "admin_name": current_user.full_name
            }
        )
    
    return {
        "product_id": product.id,
        "product_name": product.name,
        "seller_id": seller.id,
        "seller_name": seller.full_name,
        "status": product.approval_status,
        "rejection_reason": product.rejection_reason,
        "updated_at": product.approval_date
    }

@router.put("/users/{user_id}/role", response_model=schemas.User)
async def update_user_role(
    user_id: int,
    role: models.UserRole,
    current_user: schemas.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    # Only company personnel can update user roles to admin or company
    if role in [models.UserRole.ADMIN, models.UserRole.COMPANY] and current_user.role != models.UserRole.COMPANY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only company personnel can assign admin or company roles"
        )
    
    # Get user
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update role
    user.role = role
    
    db.commit()
    db.refresh(user)
    
    return user

@router.put("/users/{user_id}/activate", response_model=schemas.User)
async def activate_user(
    user_id: int,
    current_user: schemas.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    # Get user
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Activate user
    user.is_active = True
    
    db.commit()
    db.refresh(user)
    
    return user

@router.put("/users/{user_id}/deactivate", response_model=schemas.User)
async def deactivate_user(
    user_id: int,
    current_user: schemas.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    # Get user
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Cannot deactivate company personnel
    if user.role == models.UserRole.COMPANY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot deactivate company personnel"
        )
    
    # Cannot deactivate yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot deactivate your own account"
        )
    
    # Deactivate user
    user.is_active = False
    
    db.commit()
    db.refresh(user)
    
    return user

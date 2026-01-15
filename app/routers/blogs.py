from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc, or_
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import logging
import re
from slugify import slugify

from .. import models, schemas
from ..database import get_db
from .auth import get_current_active_user
from ..cache import cached, invalidate_blog_cache, redis_client
from .user_permissions import has_permission

router = APIRouter()

# Helper function to check blog permissions
def check_blog_permission(user: models.User, permission: schemas.Permission, db: Session):
    """Check if user has blog permission or is admin/company"""
    if user.role in [models.UserRole.ADMIN, models.UserRole.COMPANY]:
        return True
    return has_permission(user, permission, db)

# Helper function to generate slug from title
def generate_slug(title: str, db: Session) -> str:
    """Generate a unique slug from the blog title"""
    base_slug = slugify(title)
    slug = base_slug
    counter = 1
    
    # Check if slug already exists
    while db.query(models.Blog).filter(models.Blog.slug == slug).first():
        # If slug exists, append a counter
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    return slug

@router.post("/", response_model=schemas.Blog)
async def create_blog(
    blog: schemas.BlogCreate,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new blog post"""
    # Check if user has manage_blogs permission or is admin/company
    if not check_blog_permission(current_user, schemas.Permission.MANAGE_BLOGS, db):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Generate slug if not provided
    if not blog.slug:
        blog.slug = generate_slug(blog.title, db)
    else:
        # Check if slug already exists
        existing_blog = db.query(models.Blog).filter(models.Blog.slug == blog.slug).first()
        if existing_blog:
            raise HTTPException(status_code=400, detail="Blog with this slug already exists")
    
    # Create blog
    db_blog = models.Blog(
        title=blog.title,
        slug=blog.slug,
        content=blog.content,
        excerpt=blog.excerpt,
        featured_image=blog.featured_image,
        author_id=current_user.id,
        status=blog.status,
        published_date=blog.published_date if blog.status == "published" else None,
        meta_title=blog.meta_title or blog.title,
        meta_description=blog.meta_description,
        tags=json.dumps(blog.tags) if blog.tags else None
    )
    
    db.add(db_blog)
    db.commit()
    db.refresh(db_blog)
    
    # Add featured products if provided
    if blog.featured_product_ids:
        for product_id in blog.featured_product_ids:
            product = db.query(models.Product).filter(models.Product.id == product_id).first()
            if product:
                db_blog.featured_products.append(product)
        
        db.commit()
        db.refresh(db_blog)
    
    # Invalidate cache
    if redis_client:
        invalidate_blog_cache()
    
    return db_blog

@router.get("/", response_model=schemas.BlogListResponse)
@cached(expire=300, key_prefix="blogs")  # Cache for 5 minutes
async def read_blogs(
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None,
    status: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    db: Session = Depends(get_db)
):
    """Get all blogs with optional filters"""
    query = db.query(models.Blog)
    
    # Apply search filter if provided
    if search:
        query = query.filter(
            or_(
                models.Blog.title.ilike(f"%{search}%"),
                models.Blog.content.ilike(f"%{search}%"),
                models.Blog.excerpt.ilike(f"%{search}%")
            )
        )
    
    # Apply status filter if provided
    if status:
        query = query.filter(models.Blog.status == status)
    else:
        # By default, only show published blogs
        query = query.filter(models.Blog.status == "published")
    
    # Count total results
    total = query.count()
    
    # Apply sorting
    if sort_by:
        if sort_by == "title":
            query = query.order_by(desc(models.Blog.title) if sort_order == "desc" else asc(models.Blog.title))
        elif sort_by == "published_date":
            query = query.order_by(desc(models.Blog.published_date) if sort_order == "desc" else asc(models.Blog.published_date))
        elif sort_by == "views_count":
            query = query.order_by(desc(models.Blog.views_count) if sort_order == "desc" else asc(models.Blog.views_count))
        else:
            # Default to created_at
            query = query.order_by(desc(models.Blog.created_at) if sort_order == "desc" else asc(models.Blog.created_at))
    
    # Apply pagination
    blogs = query.offset(skip).limit(limit).all()
    
    # Process blogs to handle JSON fields
    for blog in blogs:
        # Parse tags from JSON string to list
        if blog.tags and isinstance(blog.tags, str):
            try:
                blog.tags = json.loads(blog.tags)
            except:
                blog.tags = []
    
    # Calculate total pages
    pages = (total + limit - 1) // limit if limit > 0 else 1
    
    return {
        "blogs": blogs,
        "total": total,
        "page": skip // limit + 1 if limit > 0 else 1,
        "size": limit,
        "pages": pages
    }

@router.get("/admin", response_model=schemas.BlogListResponse)
async def read_admin_blogs(
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None,
    status: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all blogs for admin dashboard"""
    # Check if user has view_blogs permission or is admin/company
    if not check_blog_permission(current_user, schemas.Permission.VIEW_BLOGS, db):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    query = db.query(models.Blog)
    
    # Apply search filter if provided
    if search:
        query = query.filter(
            or_(
                models.Blog.title.ilike(f"%{search}%"),
                models.Blog.content.ilike(f"%{search}%"),
                models.Blog.excerpt.ilike(f"%{search}%")
            )
        )
    
    # Apply status filter if provided
    if status:
        query = query.filter(models.Blog.status == status)
    
    # Count total results
    total = query.count()
    
    # Apply sorting
    if sort_by:
        if sort_by == "title":
            query = query.order_by(desc(models.Blog.title) if sort_order == "desc" else asc(models.Blog.title))
        elif sort_by == "published_date":
            query = query.order_by(desc(models.Blog.published_date) if sort_order == "desc" else asc(models.Blog.published_date))
        elif sort_by == "views_count":
            query = query.order_by(desc(models.Blog.views_count) if sort_order == "desc" else asc(models.Blog.views_count))
        elif sort_by == "status":
            query = query.order_by(desc(models.Blog.status) if sort_order == "desc" else asc(models.Blog.status))
        else:
            # Default to created_at
            query = query.order_by(desc(models.Blog.created_at) if sort_order == "desc" else asc(models.Blog.created_at))
    
    # Apply pagination
    blogs = query.offset(skip).limit(limit).all()
    
    # Process blogs to handle JSON fields
    for blog in blogs:
        # Parse tags from JSON string to list
        if blog.tags and isinstance(blog.tags, str):
            try:
                blog.tags = json.loads(blog.tags)
            except:
                blog.tags = []
    
    # Calculate total pages
    pages = (total + limit - 1) // limit if limit > 0 else 1
    
    return {
        "blogs": blogs,
        "total": total,
        "page": skip // limit + 1 if limit > 0 else 1,
        "size": limit,
        "pages": pages
    }

@router.get("/{slug}", response_model=schemas.Blog)
async def read_blog(
    slug: str,
    db: Session = Depends(get_db)
):
    """Get a blog by slug"""
    blog = db.query(models.Blog).filter(models.Blog.slug == slug).first()
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    
    # If blog is not published, only admins and company personnel can view it
    if blog.status != "published":
        try:
            current_user = await get_current_active_user()
            if current_user.role not in [models.UserRole.ADMIN, models.UserRole.COMPANY]:
                raise HTTPException(status_code=403, detail="Not enough permissions")
        except:
            raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Parse tags from JSON string to list
    if blog.tags and isinstance(blog.tags, str):
        try:
            blog.tags = json.loads(blog.tags)
        except:
            blog.tags = []
    
    # Increment views count
    blog.views_count += 1
    db.commit()
    
    return blog

@router.get("/{blog_id}/admin", response_model=schemas.Blog)
async def read_blog_admin(
    blog_id: int,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a blog by ID for admin dashboard"""
    # Check if user has view_blogs permission or is admin/company
    if not check_blog_permission(current_user, schemas.Permission.VIEW_BLOGS, db):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    blog = db.query(models.Blog).filter(models.Blog.id == blog_id).first()
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    
    # Parse tags from JSON string to list
    if blog.tags and isinstance(blog.tags, str):
        try:
            blog.tags = json.loads(blog.tags)
        except:
            blog.tags = []
    
    return blog

@router.put("/{blog_id}", response_model=schemas.Blog)
async def update_blog(
    blog_id: int,
    blog_update: schemas.BlogUpdate,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a blog"""
    # Check if user has manage_blogs permission or is admin/company
    if not check_blog_permission(current_user, schemas.Permission.MANAGE_BLOGS, db):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    db_blog = db.query(models.Blog).filter(models.Blog.id == blog_id).first()
    if not db_blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    
    # Update slug if title is changed and slug is not provided
    if blog_update.title and not blog_update.slug:
        db_blog.slug = generate_slug(blog_update.title, db)
    elif blog_update.slug:
        # Check if slug already exists for another blog
        existing_blog = db.query(models.Blog).filter(
            models.Blog.slug == blog_update.slug,
            models.Blog.id != blog_id
        ).first()
        if existing_blog:
            raise HTTPException(status_code=400, detail="Blog with this slug already exists")
        db_blog.slug = blog_update.slug
    
    # Update fields if provided
    if blog_update.title is not None:
        db_blog.title = blog_update.title
    
    if blog_update.content is not None:
        db_blog.content = blog_update.content
    
    if blog_update.excerpt is not None:
        db_blog.excerpt = blog_update.excerpt
    
    if blog_update.featured_image is not None:
        db_blog.featured_image = blog_update.featured_image
    
    if blog_update.status is not None:
        db_blog.status = blog_update.status
        # Update published_date if status is changed to published
        if blog_update.status == "published" and db_blog.published_date is None:
            db_blog.published_date = datetime.now()
    
    if blog_update.published_date is not None:
        db_blog.published_date = blog_update.published_date
    
    if blog_update.meta_title is not None:
        db_blog.meta_title = blog_update.meta_title
    
    if blog_update.meta_description is not None:
        db_blog.meta_description = blog_update.meta_description
    
    if blog_update.tags is not None:
        db_blog.tags = json.dumps(blog_update.tags)
    
    # Update featured products if provided
    if blog_update.featured_product_ids is not None:
        # Clear existing featured products
        db_blog.featured_products = []
        
        # Add new featured products
        for product_id in blog_update.featured_product_ids:
            product = db.query(models.Product).filter(models.Product.id == product_id).first()
            if product:
                db_blog.featured_products.append(product)
    
    db.commit()
    db.refresh(db_blog)
    
    # Invalidate cache
    if redis_client:
        invalidate_blog_cache()
    
    # Parse tags from JSON string to list for response
    if db_blog.tags and isinstance(db_blog.tags, str):
        try:
            db_blog.tags = json.loads(db_blog.tags)
        except:
            db_blog.tags = []
    
    return db_blog

@router.delete("/{blog_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_blog(
    blog_id: int,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a blog"""
    # Check if user has manage_blogs permission or is admin/company
    if not check_blog_permission(current_user, schemas.Permission.MANAGE_BLOGS, db):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    db_blog = db.query(models.Blog).filter(models.Blog.id == blog_id).first()
    if not db_blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    
    # Get slug for cache invalidation
    slug = db_blog.slug
    
    # Delete blog
    db.delete(db_blog)
    db.commit()
    
    # Invalidate cache
    if redis_client:
        invalidate_blog_cache()
    
    return {"status": "success"}

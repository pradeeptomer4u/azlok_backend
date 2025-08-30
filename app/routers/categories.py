from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
from typing import List, Optional, Dict
from datetime import datetime
import logging

from .. import models, schemas
from ..database import get_db
from .auth import get_current_active_user
from ..cache import cached, invalidate_categories_cache, redis_client

router = APIRouter()

def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from a category name"""
    return name.lower().replace(" ", "-")

@router.post("/", response_model=schemas.Category)
async def create_category(
    category: schemas.CategoryCreate,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Only admins and company personnel can create categories
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.COMPANY]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Generate slug if not provided
    if not category.slug:
        category.slug = generate_slug(category.name)
    
    # Check if slug already exists
    existing_category = db.query(models.Category).filter(models.Category.slug == category.slug).first()
    if existing_category:
        raise HTTPException(status_code=400, detail="Category with this slug already exists")
    
    # Check if parent category exists if provided
    if category.parent_id:
        parent_category = db.query(models.Category).filter(models.Category.id == category.parent_id).first()
        if not parent_category:
            raise HTTPException(status_code=404, detail="Parent category not found")
    
    # Create category
    db_category = models.Category(
        name=category.name,
        slug=category.slug,
        description=category.description,
        image_url=category.image_url,
        parent_id=category.parent_id
    )
    
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    
    # Invalidate categories cache after creation
    invalidate_categories_cache()
    
    # Store category in Redis for faster access
    category_data = {
        "id": db_category.id,
        "name": db_category.name,
        "slug": db_category.slug,
        "description": db_category.description,
        "parent_id": db_category.parent_id
    }
    
    # Safely update Redis if available
    if redis_client is not None:
        try:
            redis_client.hset(f"category:{db_category.id}", mapping=category_data)
        except Exception as e:
            # Log error but continue - Redis is optional
            logging.warning(f"Failed to store category in Redis: {e}")
    
    return db_category

@router.get("/", response_model=List[schemas.Category])
@cached(expire=600, key_prefix="categories")  # Cache for 10 minutes
async def read_categories(
    skip: int = 0,
    limit: int = 100,
    parent_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(models.Category)
    
    if parent_id is not None:
        query = query.filter(models.Category.parent_id == parent_id)
    else:
        # If no parent_id specified, return top-level categories (parent_id is None)
        query = query.filter(models.Category.parent_id.is_(None))
    
    categories = query.offset(skip).limit(limit).all()
    return [schemas.Category.from_orm(cat) for cat in categories]

@router.get("/all", response_model=List[schemas.Category])
@cached(expire=600, key_prefix="categories")  # Cache for 10 minutes
async def read_all_categories(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    # Get all categories regardless of parent
    categories = db.query(models.Category).offset(skip).limit(limit).all()
    return [schemas.Category.from_orm(cat) for cat in categories]

@router.get("/{category_id}", response_model=schemas.Category)
@cached(expire=600, key_prefix="categories")  # Cache for 10 minutes
async def read_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return schemas.Category.from_orm(category)

@router.put("/{category_id}", response_model=schemas.Category)
async def update_category(
    category_id: int,
    category_update: schemas.CategoryUpdate,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Only admins and company personnel can update categories
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.COMPANY]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    db_category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Update category fields if provided
    if category_update.name is not None:
        db_category.name = category_update.name
    
    if category_update.description is not None:
        db_category.description = category_update.description
    
    if category_update.image_url is not None:
        db_category.image_url = category_update.image_url
    
    if category_update.parent_id is not None:
        # Check if parent category exists
        if category_update.parent_id > 0:
            parent_category = db.query(models.Category).filter(models.Category.id == category_update.parent_id).first()
            if not parent_category:
                raise HTTPException(status_code=404, detail="Parent category not found")
            
            # Check for circular reference
            if category_update.parent_id == category_id:
                raise HTTPException(status_code=400, detail="Category cannot be its own parent")
        
        db_category.parent_id = category_update.parent_id if category_update.parent_id > 0 else None
    
    db.commit()
    db.refresh(db_category)
    
    # Update category in Redis
    category_data = {
        "id": db_category.id,
        "name": db_category.name,
        "slug": db_category.slug,
        "description": db_category.description,
        "parent_id": db_category.parent_id
    }
    
    # Safely update Redis if available
    if redis_client is not None:
        try:
            redis_client.hset(f"category:{db_category.id}", mapping=category_data)
        except Exception as e:
            # Log error but continue - Redis is optional
            logging.warning(f"Failed to update category in Redis: {e}")
    
    return db_category

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Only admins and company personnel can delete categories
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.COMPANY]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Check if category exists
    db_category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Check if category has subcategories
    subcategories = db.query(models.Category).filter(models.Category.parent_id == category_id).count()
    if subcategories > 0:
        raise HTTPException(status_code=400, detail="Cannot delete category with subcategories")
    
    # Check if category has products
    products = db.query(models.Product).join(models.Product.categories).filter(models.Category.id == category_id).count()
    if products > 0:
        raise HTTPException(status_code=400, detail="Cannot delete category with products")
    
    # Delete category from Redis
    if redis_client is not None:
        try:
            redis_client.delete(f"category:{db_category.id}")
        except Exception as e:
            # Log error but continue - Redis is optional
            logging.warning(f"Failed to delete category from Redis: {e}")
    
    # Delete category from database
    db.delete(db_category)
    db.commit()
    
    return {"status": "success"}

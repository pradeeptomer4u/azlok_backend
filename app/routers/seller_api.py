from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import models, schemas
from ..database import get_db

router = APIRouter()

@router.get("/top", response_model=List[schemas.Seller])
async def get_top_sellers(
    size: int = Query(4, ge=1, le=10),
    db: Session = Depends(get_db)
):
    """
    Get top sellers based on rating and sales
    """
    # Query sellers with role=SELLER
    sellers_query = db.query(models.User).filter(
        models.User.role == models.UserRole.SELLER,
        models.User.is_active == True
    )
    
    # Order by rating (if available) or join date
    sellers = sellers_query.order_by(
        models.User.rating.desc() if hasattr(models.User, 'rating') else models.User.created_at.desc()
    ).limit(size).all()
    
    # Transform to Seller schema
    result = []
    for seller in sellers:
        # Get product count for this seller
        product_count = db.query(models.Product).filter(
            models.Product.seller_id == seller.id
        ).count()
        
        # Parse business address if it exists
        business_address = {}
        if hasattr(seller, 'business_address') and seller.business_address:
            try:
                import json
                if isinstance(seller.business_address, str):
                    business_address = json.loads(seller.business_address)
                elif isinstance(seller.business_address, dict):
                    business_address = seller.business_address
            except:
                business_address = {}
        
        # Create seller response object
        seller_data = {
            "id": seller.id,
            "username": seller.username,
            "full_name": seller.full_name,
            "business_name": getattr(seller, 'business_name', seller.full_name),
            "business_address": business_address,
            "region": getattr(seller, 'region', None),
            "rating": getattr(seller, 'rating', 4.5),  # Default rating if not available
            "total_sales": None,  # Would need to calculate from orders
            "product_count": product_count,
            "joined_date": seller.created_at,
            "verified": True,  # Default to verified
            "image_url": None  # No image URL in the model
        }
        result.append(schemas.Seller(**seller_data))
    
    return result

@router.get("/{seller_id}", response_model=schemas.Seller)
async def get_seller_by_id(
    seller_id: int,
    db: Session = Depends(get_db)
):
    """
    Get seller details by ID
    """
    seller = db.query(models.User).filter(
        models.User.id == seller_id,
        models.User.role == models.UserRole.SELLER,
        models.User.is_active == True
    ).first()
    
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    
    # Get product count for this seller
    product_count = db.query(models.Product).filter(
        models.Product.seller_id == seller.id
    ).count()
    
    # Parse business address if it exists
    business_address = {}
    if hasattr(seller, 'business_address') and seller.business_address:
        try:
            import json
            if isinstance(seller.business_address, str):
                business_address = json.loads(seller.business_address)
            elif isinstance(seller.business_address, dict):
                business_address = seller.business_address
        except:
            business_address = {}
    
    # Create seller response object
    seller_data = {
        "id": seller.id,
        "username": seller.username,
        "full_name": seller.full_name,
        "business_name": getattr(seller, 'business_name', seller.full_name),
        "business_address": business_address,
        "region": getattr(seller, 'region', None),
        "rating": getattr(seller, 'rating', 4.5),  # Default rating if not available
        "total_sales": None,  # Would need to calculate from orders
        "product_count": product_count,
        "joined_date": seller.created_at,
        "verified": True,  # Default to verified
        "image_url": None  # No image URL in the model
    }
    
    return schemas.Seller(**seller_data)

@router.get("/slug/{slug}", response_model=schemas.Seller)
async def get_seller_by_slug(
    slug: str,
    db: Session = Depends(get_db)
):
    """
    Get seller details by slug
    """
    # Convert slug to username format (replace hyphens with underscores)
    username = slug.replace('-', '_')
    
    seller = db.query(models.User).filter(
        models.User.username == username,
        models.User.role == models.UserRole.SELLER,
        models.User.is_active == True
    ).first()
    
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    
    # Get product count for this seller
    product_count = db.query(models.Product).filter(
        models.Product.seller_id == seller.id
    ).count()
    
    # Parse business address if it exists
    business_address = {}
    if hasattr(seller, 'business_address') and seller.business_address:
        try:
            import json
            if isinstance(seller.business_address, str):
                business_address = json.loads(seller.business_address)
            elif isinstance(seller.business_address, dict):
                business_address = seller.business_address
        except:
            business_address = {}
    
    # Create seller response object
    seller_data = {
        "id": seller.id,
        "username": seller.username,
        "full_name": seller.full_name,
        "business_name": getattr(seller, 'business_name', seller.full_name),
        "business_address": business_address,
        "region": getattr(seller, 'region', None),
        "rating": getattr(seller, 'rating', 4.5),  # Default rating if not available
        "total_sales": None,  # Would need to calculate from orders
        "product_count": product_count,
        "joined_date": seller.created_at,
        "verified": True,  # Default to verified
        "image_url": None  # No image URL in the model
    }
    
    return schemas.Seller(**seller_data)

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
from typing import List, Optional, Dict
from datetime import datetime

from .. import models, schemas
from ..database import get_db
from .auth import get_current_active_user

router = APIRouter()

# Helper function to check admin permissions
async def get_admin_user(current_user: schemas.User = Depends(get_current_active_user)):
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    return current_user

# Helper function to check seller or admin permissions
async def get_seller_or_admin_user(current_user: schemas.User = Depends(get_current_active_user)):
    if current_user.role not in [models.UserRole.SELLER, models.UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers or admins can access this endpoint"
        )
    return current_user

# Get all tax rates
@router.get("/tax-rates", response_model=List[Dict])
async def get_tax_rates(
    tax_type: Optional[models.TaxType] = None,
    region: Optional[str] = None,
    category_id: Optional[int] = None,
    is_active: bool = True,
    current_user: schemas.User = Depends(get_seller_or_admin_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.TaxRate).filter(models.TaxRate.is_active == is_active)
    
    if tax_type:
        query = query.filter(models.TaxRate.tax_type == tax_type)
    
    if region:
        query = query.filter(models.TaxRate.region == region)
    
    if category_id:
        query = query.filter(models.TaxRate.category_id == category_id)
    
    tax_rates = query.all()
    
    result = []
    for tax_rate in tax_rates:
        category_name = None
        if tax_rate.category_id:
            category = db.query(models.Category).filter(models.Category.id == tax_rate.category_id).first()
            if category:
                category_name = category.name
        
        result.append({
            "id": tax_rate.id,
            "tax_type": tax_rate.tax_type,
            "rate": tax_rate.rate,
            "category_id": tax_rate.category_id,
            "category_name": category_name,
            "region": tax_rate.region,
            "is_active": tax_rate.is_active,
            "effective_from": tax_rate.effective_from,
            "effective_to": tax_rate.effective_to
        })
    
    return result

# Create tax rate (admin only)
@router.post("/tax-rates", status_code=status.HTTP_201_CREATED)
async def create_tax_rate(
    tax_rate: schemas.TaxRateCreate,
    current_user: schemas.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    # Check if category exists if provided
    if tax_rate.category_id:
        category = db.query(models.Category).filter(models.Category.id == tax_rate.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category not found"
            )
    
    # Create tax rate
    db_tax_rate = models.TaxRate(
        tax_type=tax_rate.tax_type,
        rate=tax_rate.rate,
        category_id=tax_rate.category_id,
        region=tax_rate.region,
        is_active=tax_rate.is_active,
        effective_from=tax_rate.effective_from,
        effective_to=tax_rate.effective_to
    )
    
    db.add(db_tax_rate)
    db.commit()
    db.refresh(db_tax_rate)
    
    return db_tax_rate

# Update tax rate (admin only)
@router.put("/tax-rates/{tax_rate_id}")
async def update_tax_rate(
    tax_rate_id: int,
    tax_rate_update: schemas.TaxRateUpdate,
    current_user: schemas.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    # Get tax rate
    db_tax_rate = db.query(models.TaxRate).filter(models.TaxRate.id == tax_rate_id).first()
    
    if not db_tax_rate:
        raise HTTPException(status_code=404, detail="Tax rate not found")
    
    # Check if category exists if provided
    if tax_rate_update.category_id:
        category = db.query(models.Category).filter(models.Category.id == tax_rate_update.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category not found"
            )
    
    # Update fields if provided
    update_data = tax_rate_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_tax_rate, key, value)
    
    db.commit()
    db.refresh(db_tax_rate)
    
    return db_tax_rate

# Delete tax rate (admin only)
@router.delete("/tax-rates/{tax_rate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tax_rate(
    tax_rate_id: int,
    current_user: schemas.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    # Get tax rate
    db_tax_rate = db.query(models.TaxRate).filter(models.TaxRate.id == tax_rate_id).first()
    
    if not db_tax_rate:
        raise HTTPException(status_code=404, detail="Tax rate not found")
    
    # Delete tax rate
    db.delete(db_tax_rate)
    db.commit()
    
    return None

# Get all margin settings
@router.get("/margin-settings", response_model=List[Dict])
async def get_margin_settings(
    product_id: Optional[int] = None,
    category_id: Optional[int] = None,
    seller_id: Optional[int] = None,
    region: Optional[str] = None,
    is_active: bool = True,
    current_user: schemas.User = Depends(get_seller_or_admin_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.MarginSetting).filter(models.MarginSetting.is_active == is_active)
    
    # Non-admin users can only see their own margin settings
    if current_user.role != models.UserRole.ADMIN:
        query = query.filter(models.MarginSetting.seller_id == current_user.id)
    
    if product_id:
        query = query.filter(models.MarginSetting.product_id == product_id)
    
    if category_id:
        query = query.filter(models.MarginSetting.category_id == category_id)
    
    if seller_id and current_user.role == models.UserRole.ADMIN:
        query = query.filter(models.MarginSetting.seller_id == seller_id)
    
    if region:
        query = query.filter(models.MarginSetting.region == region)
    
    margin_settings = query.all()
    
    result = []
    for margin in margin_settings:
        product_name = None
        if margin.product_id:
            product = db.query(models.Product).filter(models.Product.id == margin.product_id).first()
            if product:
                product_name = product.name
        
        category_name = None
        if margin.category_id:
            category = db.query(models.Category).filter(models.Category.id == margin.category_id).first()
            if category:
                category_name = category.name
        
        seller_name = None
        if margin.seller_id:
            seller = db.query(models.User).filter(models.User.id == margin.seller_id).first()
            if seller:
                seller_name = seller.full_name
        
        result.append({
            "id": margin.id,
            "margin_percentage": margin.margin_percentage,
            "product_id": margin.product_id,
            "product_name": product_name,
            "category_id": margin.category_id,
            "category_name": category_name,
            "seller_id": margin.seller_id,
            "seller_name": seller_name,
            "region": margin.region,
            "is_active": margin.is_active
        })
    
    return result

# Create margin setting (admin only)
@router.post("/margin-settings", status_code=status.HTTP_201_CREATED)
async def create_margin_setting(
    margin_setting: schemas.MarginSettingCreate,
    current_user: schemas.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    # Validate references
    if margin_setting.product_id:
        product = db.query(models.Product).filter(models.Product.id == margin_setting.product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product not found"
            )
    
    if margin_setting.category_id:
        category = db.query(models.Category).filter(models.Category.id == margin_setting.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category not found"
            )
    
    if margin_setting.seller_id:
        seller = db.query(models.User).filter(
            models.User.id == margin_setting.seller_id,
            models.User.role == models.UserRole.SELLER
        ).first()
        if not seller:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seller not found"
            )
    
    # Create margin setting
    db_margin = models.MarginSetting(
        margin_percentage=margin_setting.margin_percentage,
        product_id=margin_setting.product_id,
        category_id=margin_setting.category_id,
        seller_id=margin_setting.seller_id,
        region=margin_setting.region,
        is_active=margin_setting.is_active
    )
    
    db.add(db_margin)
    db.commit()
    db.refresh(db_margin)
    
    return db_margin

# Update margin setting (admin only)
@router.put("/margin-settings/{margin_id}")
async def update_margin_setting(
    margin_id: int,
    margin_update: schemas.MarginSettingUpdate,
    current_user: schemas.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    # Get margin setting
    db_margin = db.query(models.MarginSetting).filter(models.MarginSetting.id == margin_id).first()
    
    if not db_margin:
        raise HTTPException(status_code=404, detail="Margin setting not found")
    
    # Validate references
    if margin_update.product_id:
        product = db.query(models.Product).filter(models.Product.id == margin_update.product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product not found"
            )
    
    if margin_update.category_id:
        category = db.query(models.Category).filter(models.Category.id == margin_update.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category not found"
            )
    
    if margin_update.seller_id:
        seller = db.query(models.User).filter(
            models.User.id == margin_update.seller_id,
            models.User.role == models.UserRole.SELLER
        ).first()
        if not seller:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seller not found"
            )
    
    # Update fields if provided
    update_data = margin_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_margin, key, value)
    
    db.commit()
    db.refresh(db_margin)
    
    return db_margin

# Delete margin setting (admin only)
@router.delete("/margin-settings/{margin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_margin_setting(
    margin_id: int,
    current_user: schemas.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    # Get margin setting
    db_margin = db.query(models.MarginSetting).filter(models.MarginSetting.id == margin_id).first()
    
    if not db_margin:
        raise HTTPException(status_code=404, detail="Margin setting not found")
    
    # Delete margin setting
    db.delete(db_margin)
    db.commit()
    
    return None

# Calculate tax for a product
@router.post("/calculate-tax", response_model=Dict)
async def calculate_tax(
    tax_request: schemas.TaxCalculationRequest,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Get product
    product = db.query(models.Product).filter(models.Product.id == tax_request.product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get applicable tax rate
    tax_rate = None
    
    # First try to find product-specific tax rate via HSN code
    if product.hsn_code:
        tax_rate = db.query(models.TaxRate).filter(
            models.TaxRate.is_active == True,
            models.TaxRate.tax_type == models.TaxType.GST,
            func.lower(models.TaxRate.hsn_code) == func.lower(product.hsn_code)
        ).first()
    
    # If not found, try to find category-specific tax rate
    if not tax_rate and product.categories:
        category_ids = [category.id for category in product.categories]
        tax_rate = db.query(models.TaxRate).filter(
            models.TaxRate.is_active == True,
            models.TaxRate.category_id.in_(category_ids)
        ).first()
    
    # If not found, try to find region-specific tax rate
    if not tax_rate and tax_request.region:
        tax_rate = db.query(models.TaxRate).filter(
            models.TaxRate.is_active == True,
            models.TaxRate.region == tax_request.region
        ).first()
    
    # If still not found, use default tax rate
    if not tax_rate:
        tax_rate = db.query(models.TaxRate).filter(
            models.TaxRate.is_active == True,
            models.TaxRate.category_id == None,
            models.TaxRate.region == None
        ).first()
    
    # Calculate tax
    base_price = product.price
    tax_percentage = tax_rate.rate if tax_rate else product.tax_rate
    
    # Check if price is tax inclusive
    if product.is_tax_inclusive:
        # Extract tax from price
        tax_amount = base_price - (base_price / (1 + (tax_percentage / 100)))
        price_without_tax = base_price - tax_amount
    else:
        # Add tax to price
        tax_amount = base_price * (tax_percentage / 100)
        price_without_tax = base_price
    
    price_with_tax = price_without_tax + tax_amount
    
    # Calculate GST components if applicable
    cgst_amount = 0
    sgst_amount = 0
    igst_amount = 0
    
    if tax_rate and tax_rate.tax_type == models.TaxType.GST:
        # For same state (CGST + SGST)
        if tax_request.buyer_state == tax_request.seller_state:
            cgst_amount = tax_amount / 2
            sgst_amount = tax_amount / 2
        # For different state (IGST)
        else:
            igst_amount = tax_amount
    
    return {
        "product_id": product.id,
        "product_name": product.name,
        "base_price": base_price,
        "price_without_tax": price_without_tax,
        "tax_percentage": tax_percentage,
        "tax_amount": tax_amount,
        "price_with_tax": price_with_tax,
        "is_tax_inclusive": product.is_tax_inclusive,
        "cgst_amount": cgst_amount,
        "sgst_amount": sgst_amount,
        "igst_amount": igst_amount,
        "hsn_code": product.hsn_code
    }

# Calculate tax for an entire order
@router.post("/calculate-order-tax", response_model=Dict)
async def calculate_order_tax(
    order_request: schemas.OrderTaxCalculationRequest,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    total_amount = 0
    total_tax_amount = 0
    total_cgst_amount = 0
    total_sgst_amount = 0
    total_igst_amount = 0
    items_with_tax = []
    
    for item in order_request.items:
        # Get product
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with ID {item.product_id} not found")
        
        # Get seller state
        seller = db.query(models.User).filter(models.User.id == product.seller_id).first()
        seller_state = None
        if seller and seller.business_address:
            try:
                address_data = seller.business_address
                if isinstance(address_data, str):
                    import json
                    address_data = json.loads(address_data)
                seller_state = address_data.get("state")
            except:
                pass
        
        # Calculate tax for this item
        tax_calculation = await calculate_tax(
            schemas.TaxCalculationRequest(
                product_id=product.id,
                quantity=item.quantity,
                region=order_request.region,
                buyer_state=order_request.buyer_state,
                seller_state=seller_state
            ),
            current_user,
            db
        )
        
        # Calculate item totals
        item_total = tax_calculation["price_with_tax"] * item.quantity
        item_tax_total = tax_calculation["tax_amount"] * item.quantity
        item_cgst_total = tax_calculation["cgst_amount"] * item.quantity
        item_sgst_total = tax_calculation["sgst_amount"] * item.quantity
        item_igst_total = tax_calculation["igst_amount"] * item.quantity
        
        # Add to order totals
        total_amount += item_total
        total_tax_amount += item_tax_total
        total_cgst_amount += item_cgst_total
        total_sgst_amount += item_sgst_total
        total_igst_amount += item_igst_total
        
        # Add item details
        items_with_tax.append({
            "product_id": product.id,
            "product_name": product.name,
            "quantity": item.quantity,
            "unit_price": product.price,
            "unit_tax": tax_calculation["tax_amount"],
            "unit_cgst": tax_calculation["cgst_amount"],
            "unit_sgst": tax_calculation["sgst_amount"],
            "unit_igst": tax_calculation["igst_amount"],
            "item_total": item_total,
            "hsn_code": product.hsn_code
        })
    
    # Calculate shipping tax if applicable
    shipping_tax_amount = 0
    if order_request.shipping_amount > 0 and order_request.apply_tax_to_shipping:
        # Default shipping tax rate (can be configured)
        shipping_tax_rate = 18.0  # 18% GST on shipping
        shipping_tax_amount = order_request.shipping_amount * (shipping_tax_rate / 100)
        
        # Add shipping tax to totals
        total_tax_amount += shipping_tax_amount
        total_amount += order_request.shipping_amount + shipping_tax_amount
        
        # Split shipping GST
        if order_request.buyer_state == order_request.seller_state:
            shipping_cgst = shipping_tax_amount / 2
            shipping_sgst = shipping_tax_amount / 2
            total_cgst_amount += shipping_cgst
            total_sgst_amount += shipping_sgst
        else:
            shipping_igst = shipping_tax_amount
            total_igst_amount += shipping_igst
    else:
        # Add shipping without tax
        total_amount += order_request.shipping_amount
    
    return {
        "subtotal": sum(item["unit_price"] * item["quantity"] for item in items_with_tax),
        "shipping_amount": order_request.shipping_amount,
        "shipping_tax_amount": shipping_tax_amount,
        "total_tax_amount": total_tax_amount,
        "total_cgst_amount": total_cgst_amount,
        "total_sgst_amount": total_sgst_amount,
        "total_igst_amount": total_igst_amount,
        "total_amount": total_amount,
        "items": items_with_tax
    }

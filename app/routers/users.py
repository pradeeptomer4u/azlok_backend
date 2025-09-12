from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import traceback
from datetime import datetime

from .. import models, schemas
from ..database import get_db
from .auth import get_current_active_user, get_password_hash, verify_password

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/me", response_model=schemas.User)
async def read_users_me(request: Request, current_user: schemas.User = Depends(get_current_active_user)):
    try:
        logger.debug(f"Accessing /me endpoint with token: {request.headers.get('authorization')[:20]}...")
        logger.debug(f"Current user data: {current_user}")
        return current_user
    except Exception as e:
        logger.error(f"Error in /me endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.put("/me", response_model=schemas.User)
async def update_user_me(
    user_update: schemas.UserUpdate,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_user = db.query(models.User).filter(models.User.id == current_user.id).first()
    
    if user_update.email is not None:
        # Check if email is already taken
        existing_user = db.query(models.User).filter(models.User.email == user_update.email).first()
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(status_code=400, detail="Email already registered")
        db_user.email = user_update.email
        
    if user_update.username is not None:
        # Check if username is already taken
        existing_user = db.query(models.User).filter(models.User.username == user_update.username).first()
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(status_code=400, detail="Username already taken")
        db_user.username = user_update.username
        
    if user_update.full_name is not None:
        db_user.full_name = user_update.full_name
        
    if user_update.phone is not None:
        db_user.phone = user_update.phone
        
    if user_update.password is not None:
        db_user.hashed_password = get_password_hash(user_update.password)
    
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/{user_id}", response_model=schemas.User)
async def read_user(
    user_id: int,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Only admins and company personnel can view other users' details
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.COMPANY] and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.get("/", response_model=List[schemas.User])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    role: Optional[str] = Query(None, description="Filter users by role (e.g., 'seller', 'buyer', 'admin')"),
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Only admins and company personnel can list all users
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.COMPANY]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Start with base query
    query = db.query(models.User)
    
    # Apply role filter if provided
    if role:
        try:
            # Convert string role to enum value
            role_enum = models.UserRole[role.upper()]
            query = query.filter(models.User.role == role_enum)
        except KeyError:
            # If invalid role provided, return empty list
            return []
    
    # Apply pagination
    users = query.offset(skip).limit(limit).all()
    return users

@router.post("/delete-request", response_model=dict)
async def request_account_deletion(
    request_data: dict,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Submit a request to delete a user account.
    The request will be processed by administrators within 30 days.
    """
    # Verify the user's password
    if not verify_password(request_data.get("password", ""), current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )
    
    # Create a new deletion request
    # Since we don't have a dedicated model for deletion requests,
    # we'll update the user's metadata to include the deletion request
    user_db = db.query(models.User).filter(models.User.id == current_user.id).first()
    
    # Initialize meta_data if it doesn't exist
    if not user_db.meta_data:
        user_db.meta_data = {}
    
    # Add deletion request to meta_data
    user_db.meta_data["deletion_request"] = {
        "reason": request_data.get("reason", "No reason provided"),
        "requested_at": datetime.utcnow().isoformat(),
        "status": "pending"
    }
    
    db.commit()
    
    return {"message": "Account deletion request submitted successfully"}

@router.get("/deletion-requests", response_model=List[dict])
async def get_deletion_requests(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_active_user)
):
    """
    Get all account deletion requests (admin only).
    """
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this resource"
        )
    
    # Find all users with deletion requests
    users_with_requests = db.query(models.User).filter(
        models.User.meta_data.has_key("deletion_request")
    ).all()
    
    deletion_requests = []
    for user in users_with_requests:
        if user.meta_data and "deletion_request" in user.meta_data:
            request = user.meta_data["deletion_request"]
            deletion_requests.append({
                "user_id": user.id,
                "user_email": user.email,
                "user_name": user.full_name,
                "reason": request.get("reason", "No reason provided"),
                "requested_at": request.get("requested_at"),
                "status": request.get("status", "pending"),
                "processed_at": request.get("processed_at"),
                "processed_by": request.get("processed_by")
            })
    
    return deletion_requests

@router.put("/deletion-requests/{user_id}/approve")
async def approve_deletion_request(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_active_user)
):
    """
    Approve an account deletion request (admin only).
    """
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this resource"
        )
    
    # Get the user to delete
    user_to_delete = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if there's a deletion request
    if not user_to_delete.meta_data or "deletion_request" not in user_to_delete.meta_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deletion request not found"
        )
    
    # Update the request status
    user_to_delete.meta_data["deletion_request"]["status"] = "approved"
    user_to_delete.meta_data["deletion_request"]["processed_at"] = datetime.utcnow().isoformat()
    user_to_delete.meta_data["deletion_request"]["processed_by"] = current_user.id
    
    # Anonymize the user data instead of deleting
    user_to_delete.email = f"deleted_user_{user_to_delete.id}@deleted.com"
    user_to_delete.username = f"deleted_user_{user_to_delete.id}"
    user_to_delete.full_name = "Deleted User"
    user_to_delete.phone = None
    user_to_delete.is_active = False
    
    db.commit()
    
    return {"message": "Account deletion request approved and user data anonymized"}

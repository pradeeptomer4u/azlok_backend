from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
import logging
import traceback

from .. import models, schemas
from ..database import get_db
from .auth import get_current_active_user, get_password_hash

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
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Only admins and company personnel can list all users
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.COMPANY]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users

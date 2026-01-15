from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone

from .. import models
from ..schemas_permissions import (
    UserPermissionCreate,
    UserPermissionResponse,
    UserPermissionsUpdate,
    UserWithPermissions,
    PermissionCheckRequest,
    PermissionCheckResponse
)
from ..schemas import Permission
from ..database import get_db
from .auth import get_current_active_user, get_admin_user

router = APIRouter()

# Helper function to check if user has permission
def has_permission(user: models.User, permission: Permission, db: Session) -> bool:
    """Check if user has a specific permission"""
    # Admins have all permissions
    if user.role in [models.UserRole.ADMIN, models.UserRole.COMPANY]:
        return True
    
    # Check user-specific permissions
    user_permission = db.query(models.UserPermission).filter(
        models.UserPermission.user_id == user.id,
        models.UserPermission.permission == permission,
        models.UserPermission.is_active == True
    ).first()
    
    if not user_permission:
        return False
    
    # Check if permission has expired
    if user_permission.expires_at and user_permission.expires_at < datetime.now(timezone.utc):
        return False
    
    return True

# Dependency to check specific permission
def require_permission(permission: Permission):
    """Dependency to check if current user has specific permission"""
    def permission_checker(
        current_user: models.User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ):
        if not has_permission(current_user, permission, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You don't have permission: {permission.value}"
            )
        return current_user
    return permission_checker

@router.get("/users/{user_id}/permissions", response_model=List[UserPermissionResponse])
async def get_user_permissions(
    user_id: int,
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get all permissions for a specific user"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    permissions = db.query(models.UserPermission).filter(
        models.UserPermission.user_id == user_id
    ).all()
    
    return permissions

@router.post("/users/{user_id}/permissions", response_model=UserPermissionResponse)
async def grant_permission(
    user_id: int,
    permission_data: UserPermissionCreate,
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Grant a permission to a user"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if permission already exists
    existing = db.query(models.UserPermission).filter(
        models.UserPermission.user_id == user_id,
        models.UserPermission.permission == permission_data.permission
    ).first()
    
    if existing:
        # Update existing permission
        existing.is_active = True
        existing.expires_at = permission_data.expires_at
        existing.granted_by = current_user.id
        existing.granted_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return existing
    
    # Create new permission
    new_permission = models.UserPermission(
        user_id=user_id,
        permission=permission_data.permission,
        granted_by=current_user.id,
        expires_at=permission_data.expires_at,
        is_active=permission_data.is_active
    )
    
    db.add(new_permission)
    db.commit()
    db.refresh(new_permission)
    
    return new_permission

@router.put("/users/{user_id}/permissions/bulk", response_model=UserWithPermissions)
async def update_user_permissions_bulk(
    user_id: int,
    permissions_update: UserPermissionsUpdate,
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Update all permissions for a user at once"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Deactivate all existing permissions
    db.query(models.UserPermission).filter(
        models.UserPermission.user_id == user_id
    ).update({"is_active": False})
    
    # Add/activate new permissions
    for permission in permissions_update.permissions:
        existing = db.query(models.UserPermission).filter(
            models.UserPermission.user_id == user_id,
            models.UserPermission.permission == permission
        ).first()
        
        if existing:
            existing.is_active = True
            existing.granted_by = current_user.id
            existing.granted_at = datetime.now(timezone.utc)
        else:
            new_permission = models.UserPermission(
                user_id=user_id,
                permission=permission,
                granted_by=current_user.id,
                is_active=True
            )
            db.add(new_permission)
    
    db.commit()
    
    # Get updated user with permissions
    user_permissions = db.query(models.UserPermission).filter(
        models.UserPermission.user_id == user_id,
        models.UserPermission.is_active == True
    ).all()
    
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "permissions": [p.permission for p in user_permissions]
    }

@router.delete("/users/{user_id}/permissions/{permission}")
async def revoke_permission(
    user_id: int,
    permission: Permission,
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Revoke a specific permission from a user"""
    user_permission = db.query(models.UserPermission).filter(
        models.UserPermission.user_id == user_id,
        models.UserPermission.permission == permission
    ).first()
    
    if not user_permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    
    user_permission.is_active = False
    db.commit()
    
    return {"message": f"Permission {permission.value} revoked from user {user_id}"}

@router.post("/check-permission", response_model=PermissionCheckResponse)
async def check_permission(
    permission_check: PermissionCheckRequest,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Check if current user has a specific permission"""
    has_perm = has_permission(current_user, permission_check.permission, db)
    
    return {
        "has_permission": has_perm,
        "permission": permission_check.permission
    }

@router.get("/my-permissions", response_model=List[Permission])
async def get_my_permissions(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all permissions for the current user"""
    # Admins have all permissions
    if current_user.role in [models.UserRole.ADMIN, models.UserRole.COMPANY]:
        return [p for p in Permission]
    
    # Get user-specific permissions
    user_permissions = db.query(models.UserPermission).filter(
        models.UserPermission.user_id == current_user.id,
        models.UserPermission.is_active == True
    ).all()
    
    # Filter out expired permissions
    active_permissions = []
    for perm in user_permissions:
        if not perm.expires_at or perm.expires_at > datetime.now(timezone.utc):
            active_permissions.append(perm.permission)
    
    return active_permissions

@router.get("/all-permissions", response_model=List[str])
async def get_all_available_permissions(
    current_user: models.User = Depends(get_admin_user)
):
    """Get list of all available permissions"""
    return [p.value for p in Permission]

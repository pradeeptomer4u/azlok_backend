from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from .schemas import Permission

# Permission schemas
class UserPermissionBase(BaseModel):
    permission: Permission
    expires_at: Optional[datetime] = None
    is_active: bool = True

class UserPermissionCreate(UserPermissionBase):
    user_id: int

class UserPermissionUpdate(BaseModel):
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None

class UserPermissionResponse(UserPermissionBase):
    id: int
    user_id: int
    granted_by: Optional[int] = None
    granted_at: datetime
    
    class Config:
        from_attributes = True

class UserPermissionsUpdate(BaseModel):
    user_id: int
    permissions: List[Permission]

class UserWithPermissions(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    permissions: List[Permission]
    
    class Config:
        from_attributes = True

class PermissionCheckRequest(BaseModel):
    permission: Permission

class PermissionCheckResponse(BaseModel):
    has_permission: bool
    permission: Permission

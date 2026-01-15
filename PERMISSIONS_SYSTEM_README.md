# User Permission Management System

## Overview
This system provides granular permission management for users in the Azlok platform. Admins can assign specific permissions to users, controlling their access to different features like blogs, orders, inventory, tax rates, etc.

## Backend Implementation

### 1. Database Models

#### Permission Enum (`app/models.py`)
```python
class Permission(str, enum.Enum):
    MANAGE_BLOGS = "manage_blogs"
    VIEW_BLOGS = "view_blogs"
    MANAGE_ORDERS = "manage_orders"
    VIEW_ORDERS = "view_orders"
    MANAGE_INVENTORY = "manage_inventory"
    VIEW_INVENTORY = "view_inventory"
    MANAGE_TAX_RATES = "manage_tax_rates"
    VIEW_TAX_RATES = "view_tax_rates"
    MANAGE_PRODUCTS = "manage_products"
    VIEW_PRODUCTS = "view_products"
    MANAGE_USERS = "manage_users"
    VIEW_USERS = "view_users"
    MANAGE_CATEGORIES = "manage_categories"
    VIEW_CATEGORIES = "view_categories"
    MANAGE_COMPANIES = "manage_companies"
    VIEW_COMPANIES = "view_companies"
    MANAGE_SELLERS = "manage_sellers"
    VIEW_SELLERS = "view_sellers"
```

#### UserPermission Model
```python
class UserPermission(Base):
    __tablename__ = "user_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    permission = Column(Enum(Permission), nullable=False)
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
```

### 2. API Endpoints

All endpoints are under `/api/permissions`:

- **GET** `/users/{user_id}/permissions` - Get all permissions for a user
- **POST** `/users/{user_id}/permissions` - Grant a permission to a user
- **PUT** `/users/{user_id}/permissions/bulk` - Update all permissions at once
- **DELETE** `/users/{user_id}/permissions/{permission}` - Revoke a permission
- **POST** `/check-permission` - Check if current user has a permission
- **GET** `/my-permissions` - Get current user's permissions
- **GET** `/all-permissions` - Get list of all available permissions

### 3. Permission Checking

#### Using the helper function:
```python
from app.routers.user_permissions import has_permission

if has_permission(current_user, Permission.MANAGE_BLOGS, db):
    # User has permission
    pass
```

#### Using the dependency:
```python
from app.routers.user_permissions import require_permission

@router.post("/blogs")
async def create_blog(
    current_user: models.User = Depends(require_permission(Permission.MANAGE_BLOGS))
):
    # Only users with MANAGE_BLOGS permission can access this
    pass
```

### 4. Migration

Run the migration script to create the `user_permissions` table:

```bash
python add_user_permissions_table.py
```

## Frontend Implementation

### 1. Permission Management UI

Navigate to: `/admin/users/{user_id}/permissions`

Features:
- View user details
- Select/deselect permissions by category
- Bulk select/deselect all permissions in a category
- Save permissions with visual feedback

### 2. AuthContext Integration

The `AuthContext` now includes:
- `permissions` array in User interface
- `hasPermission(permission: string)` method
- `refreshPermissions()` method to reload permissions
- Automatic permission fetching on login

### 3. Permission Hook

Use the `usePermissions` hook for easy permission checking:

```typescript
import { usePermissions } from '@/hooks/usePermissions';

function MyComponent() {
  const { canManageBlogs, canViewOrders, isAdmin } = usePermissions();
  
  return (
    <>
      {canManageBlogs && <BlogManagementButton />}
      {canViewOrders && <OrdersList />}
    </>
  );
}
```

### 4. Conditional Navigation

Navigation items in the admin layout can be conditionally rendered based on permissions:

```typescript
const { canViewBlogs, canManageInventory } = usePermissions();

{canViewBlogs && (
  <Link href="/admin/blogs">Blogs</Link>
)}
```

## Usage Examples

### Backend: Protect an endpoint

```python
from app.routers.user_permissions import require_permission
from app.schemas import Permission

@router.post("/blogs/create")
async def create_blog(
    blog_data: BlogCreate,
    current_user: models.User = Depends(require_permission(Permission.MANAGE_BLOGS)),
    db: Session = Depends(get_db)
):
    # Only users with MANAGE_BLOGS permission can create blogs
    new_blog = models.Blog(**blog_data.dict(), author_id=current_user.id)
    db.add(new_blog)
    db.commit()
    return new_blog
```

### Frontend: Conditional rendering

```typescript
import { usePermissions } from '@/hooks/usePermissions';

export default function AdminDashboard() {
  const { canManageBlogs, canViewOrders, canManageInventory } = usePermissions();
  
  return (
    <div>
      {canManageBlogs && (
        <section>
          <h2>Blog Management</h2>
          <Link href="/admin/blogs/create">Create New Blog</Link>
        </section>
      )}
      
      {canViewOrders && (
        <section>
          <h2>Orders</h2>
          <Link href="/admin/orders">View Orders</Link>
        </section>
      )}
      
      {canManageInventory && (
        <section>
          <h2>Inventory</h2>
          <Link href="/admin/inventory">Manage Inventory</Link>
        </section>
      )}
    </div>
  );
}
```

## Permission Hierarchy

1. **Admin & Company roles**: Have ALL permissions by default
2. **Custom permissions**: Assigned per user for granular control
3. **Expiring permissions**: Can set expiration dates for temporary access

## Security Notes

- Admins and Company users always have full access
- Permissions are checked on both frontend (UX) and backend (security)
- Frontend checks are for UI/UX only - backend always validates
- Expired permissions are automatically filtered out
- Permissions can be revoked at any time

## Testing

### Test permission assignment:
```bash
curl -X PUT http://localhost:8000/api/permissions/users/1/permissions/bulk \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "permissions": ["manage_blogs", "view_orders"]}'
```

### Test permission check:
```bash
curl -X POST http://localhost:8000/api/permissions/check-permission \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"permission": "manage_blogs"}'
```

## Future Enhancements

- Role-based permission templates
- Permission groups/bundles
- Audit log for permission changes
- Time-based permission scheduling
- Permission inheritance from roles

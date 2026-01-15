"""
Script to update all routers to use the permission system
This will add permission checks to all admin-protected endpoints
"""

routers_to_update = {
    "products.py": {
        "permission_view": "VIEW_PRODUCTS",
        "permission_manage": "MANAGE_PRODUCTS",
        "endpoints": ["create", "update", "delete", "admin_list"]
    },
    "categories.py": {
        "permission_view": "VIEW_CATEGORIES", 
        "permission_manage": "MANAGE_CATEGORIES",
        "endpoints": ["create", "update", "delete", "admin_list"]
    },
    "users.py": {
        "permission_view": "VIEW_USERS",
        "permission_manage": "MANAGE_USERS", 
        "endpoints": ["list", "update", "delete"]
    },
    "inventory.py": {
        "permission_view": "VIEW_INVENTORY",
        "permission_manage": "MANAGE_INVENTORY",
        "endpoints": ["view", "update", "adjust"]
    },
    "tax.py": {
        "permission_view": "VIEW_TAX_RATES",
        "permission_manage": "MANAGE_TAX_RATES",
        "endpoints": ["create", "update", "delete", "list"]
    },
    "seller.py": {
        "permission_view": "VIEW_SELLERS",
        "permission_manage": "MANAGE_SELLERS",
        "endpoints": ["list", "approve", "reject"]
    }
}

print("=" * 70)
print("ROUTERS TO UPDATE WITH PERMISSION SYSTEM")
print("=" * 70)
print("\nThe following routers need to be updated:")
for router, config in routers_to_update.items():
    print(f"\n{router}:")
    print(f"  View Permission: {config['permission_view']}")
    print(f"  Manage Permission: {config['permission_manage']}")
    print(f"  Endpoints: {', '.join(config['endpoints'])}")

print("\n" + "=" * 70)
print("IMPLEMENTATION PATTERN")
print("=" * 70)
print("""
1. Add import: from .user_permissions import has_permission

2. Add helper function:
   def check_<module>_permission(user, permission, db):
       if user.role in [UserRole.ADMIN, UserRole.COMPANY]:
           return True
       return has_permission(user, permission, db)

3. Replace role checks with permission checks:
   OLD: if current_user.role not in [UserRole.ADMIN, UserRole.COMPANY]:
   NEW: if not check_<module>_permission(current_user, Permission.MANAGE_X, db):
""")

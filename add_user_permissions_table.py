"""
Migration script to add user_permissions table
Run this script to add the user permissions table to the database
"""
import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.database import DATABASE_URL, Base
from app.models import UserPermission, Permission
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_user_permissions_table():
    """Add user_permissions table to the database"""
    try:
        engine = create_engine(DATABASE_URL)
        
        # Create the user_permissions table
        logger.info("Creating user_permissions table...")
        Base.metadata.create_all(bind=engine, tables=[UserPermission.__table__])
        
        logger.info("✓ User permissions table created successfully!")
        logger.info(f"Available permissions: {[p.value for p in Permission]}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating user_permissions table: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("User Permissions Table Migration")
    print("=" * 60)
    print()
    
    success = add_user_permissions_table()
    
    if success:
        print()
        print("=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Restart your application")
        print("2. Use the /api/permissions endpoints to manage user permissions")
        print("3. Check /api/permissions/all-permissions for available permissions")
    else:
        print()
        print("=" * 60)
        print("Migration failed. Please check the error messages above.")
        print("=" * 60)
        sys.exit(1)

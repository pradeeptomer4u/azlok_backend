"""
Migration script to add manage_seo and view_seo to the permission enum type in PostgreSQL.
Run this script once after deploying the backend code changes.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.database import DATABASE_URL
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_seo_permissions():
    try:
        engine = create_engine(DATABASE_URL)

        with engine.connect() as conn:
            # PostgreSQL requires committing between ALTER TYPE statements
            conn.execute(text("COMMIT"))

            logger.info("Adding 'manage_seo' to permission enum...")
            conn.execute(text("ALTER TYPE permission ADD VALUE IF NOT EXISTS 'manage_seo'"))
            conn.execute(text("COMMIT"))

            logger.info("Adding 'view_seo' to permission enum...")
            conn.execute(text("ALTER TYPE permission ADD VALUE IF NOT EXISTS 'view_seo'"))
            conn.execute(text("COMMIT"))

            logger.info("✓ SEO permissions added to PostgreSQL enum successfully!")

        return True

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Add SEO Permissions Migration")
    print("=" * 60)

    success = add_seo_permissions()

    if success:
        print("\nMigration completed! Restart the backend server.")
    else:
        print("\nMigration failed. Check errors above.")
        sys.exit(1)
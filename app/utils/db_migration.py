"""
Database migration utility to add new columns and tables.
"""
import os
import sys
from sqlalchemy import text

# Add the parent directory to sys.path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.database import SessionLocal, engine

def run_migration():
    """Run database migration to add new columns and tables."""
    db = SessionLocal()
    try:
        print("Starting database migration...")
        
        # Check if meta_data column exists in users table
        check_column_sql = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='users' AND column_name='meta_data';
        """
        result = db.execute(text(check_column_sql)).fetchone()
        
        if not result:
            print("Adding meta_data column to users table...")
            add_column_sql = """
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS meta_data JSONB;
            """
            db.execute(text(add_column_sql))
            db.commit()
            print("Added meta_data column to users table")
        else:
            print("meta_data column already exists in users table")
        
        # Check if testimonials table exists
        check_table_sql = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name='testimonials';
        """
        result = db.execute(text(check_table_sql)).fetchone()
        
        if not result:
            print("Creating testimonials table...")
            create_table_sql = """
            CREATE TABLE testimonials (
                id SERIAL PRIMARY KEY,
                name VARCHAR NOT NULL,
                company VARCHAR NOT NULL,
                image VARCHAR,
                testimonial TEXT NOT NULL,
                rating INTEGER NOT NULL,
                date DATE NOT NULL DEFAULT CURRENT_DATE,
                verified BOOLEAN DEFAULT TRUE,
                user_id INTEGER REFERENCES users(id),
                meta_data JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE
            );
            CREATE INDEX idx_testimonials_user_id ON testimonials(user_id);
            """
            db.execute(text(create_table_sql))
            db.commit()
            print("Created testimonials table")
        else:
            print("testimonials table already exists")
        
        print("Database migration completed successfully!")
    except Exception as e:
        print(f"Error during migration: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()

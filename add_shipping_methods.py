import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
import re
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the DATABASE_URL from database.py
try:
    import sys
    sys.path.append('./app')
    from app.database import DATABASE_URL
    logger.info("Successfully imported DATABASE_URL from app.database")
except ImportError:
    logger.error("Failed to import DATABASE_URL from app.database")
    # Fallback to the direct connection string if import fails
    DATABASE_URL = "postgresql://neondb_owner:npg_Y0WE8ibnFjge@ep-empty-glade-a1mnqsgm-pooler.ap-southeast-1.aws.neon.tech/azlok_shopping?sslmode=require&channel_binding=require"
    logger.info("Using hardcoded DATABASE_URL as fallback")

# Parse the connection string to extract components
def parse_db_url(url):
    # Regular expression to match PostgreSQL connection string
    pattern = r'postgresql://([^:]+):([^@]+)@([^:/]+)(?::([0-9]+))?/([^?]+)'
    match = re.match(pattern, url)
    
    if match:
        user, password, host, port, dbname = match.groups()
        # Extract the database name before any query parameters
        dbname = dbname.split('?')[0]
        return {
            'user': user,
            'password': password,
            'host': host,
            'port': port or '5432',  # Default PostgreSQL port
            'dbname': dbname
        }
    else:
        raise ValueError("Invalid PostgreSQL connection string format")

def add_shipping_methods():
    """Add three shipping method entries to the database"""
    
    try:
        # Parse the DATABASE_URL
        db_config = parse_db_url(DATABASE_URL)
        
        # Connect to the database
        conn = psycopg2.connect(
            user=db_config['user'],
            password=db_config['password'],
            host=db_config['host'],
            port=db_config['port'],
            dbname=db_config['dbname']
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        # Create a cursor
        cursor = conn.cursor()
        
        # Check if shipping_methods table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'shipping_methods'
            )
        """)
        shipping_methods_exists = cursor.fetchone()[0]
        
        if not shipping_methods_exists:
            logger.error("shipping_methods table does not exist. Please run add_checkout_tables.py first.")
            return False
        
        # Check if there are already entries in the shipping_methods table
        cursor.execute("SELECT COUNT(*) FROM shipping_methods")
        count = cursor.fetchone()[0]
        
        if count > 0:
            logger.info(f"There are already {count} shipping methods in the database.")
            
            # Delete existing shipping methods if needed
            delete_existing = False  # Set to True if you want to delete existing entries
            if delete_existing:
                cursor.execute("DELETE FROM shipping_methods")
                logger.info("Deleted existing shipping methods.")
        
        # Insert three shipping method entries
        shipping_methods = [
            {
                'name': 'Express Shipping',
                'description': 'Fast delivery within 1-3 business days',
                'price': 150.0,
                'estimated_days': '1-3 days'
            },
            {
                'name': 'Standard Shipping',
                'description': 'Regular delivery within 3-5 business days',
                'price': 80.0,
                'estimated_days': '3-5 days'
            },
            {
                'name': 'Economy Shipping',
                'description': 'Budget-friendly delivery within 5-7 business days',
                'price': 50.0,
                'estimated_days': '5-7 days'
            }
        ]
        
        for method in shipping_methods:
            # Check if this shipping method already exists
            cursor.execute("""
                SELECT id FROM shipping_methods 
                WHERE name = %s AND estimated_days = %s
            """, (method['name'], method['estimated_days']))
            
            existing = cursor.fetchone()
            
            if existing:
                logger.info(f"Shipping method '{method['name']}' with estimated days '{method['estimated_days']}' already exists with ID {existing[0]}.")
            else:
                # Insert the shipping method
                cursor.execute("""
                    INSERT INTO shipping_methods (name, description, price, estimated_days, is_active)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    method['name'],
                    method['description'],
                    method['price'],
                    method['estimated_days'],
                    True
                ))
                
                new_id = cursor.fetchone()[0]
                logger.info(f"Added shipping method '{method['name']}' with ID {new_id}")
        
        # Close the connection
        cursor.close()
        conn.close()
        
        logger.info("Shipping methods added successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error adding shipping methods: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting shipping methods creation script")
    success = add_shipping_methods()
    if success:
        logger.info("Shipping methods creation completed successfully")
    else:
        logger.error("Shipping methods creation failed")

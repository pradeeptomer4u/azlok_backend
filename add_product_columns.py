import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
import re
import logging

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
        # If port is None, use default PostgreSQL port
        port = port if port else '5432'
        
        # Extract query parameters if any
        query_params = {}
        if '?' in url:
            query_string = url.split('?', 1)[1]
            for param in query_string.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    query_params[key] = value
        
        return {
            'user': user,
            'password': password,
            'host': host,
            'port': port,
            'dbname': dbname,
            'query_params': query_params
        }
    else:
        raise ValueError(f"Invalid PostgreSQL connection string format: {url}")

# Parse the DATABASE_URL
try:
    db_config = parse_db_url(DATABASE_URL)
    logger.info(f"Successfully parsed DATABASE_URL. Host: {db_config['host']}, Database: {db_config['dbname']}")
except ValueError as e:
    logger.error(f"Error parsing DATABASE_URL: {e}")
    raise

def add_columns():
    """Add features and specifications columns to the products table"""
    try:
        # Connect to the database using the parsed connection parameters
        conn_params = {
            'host': db_config['host'],
            'port': db_config['port'],
            'dbname': db_config['dbname'],
            'user': db_config['user'],
            'password': db_config['password']
        }
        
        # Add SSL parameters if they exist in the original connection string
        if 'sslmode' in db_config['query_params']:
            conn_params['sslmode'] = db_config['query_params']['sslmode']
        if 'channel_binding' in db_config['query_params']:
            conn_params['channel_binding'] = db_config['query_params']['channel_binding']
            
        logger.info(f"Connecting to database {db_config['dbname']} on host {db_config['host']}")
        conn = psycopg2.connect(**conn_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        # Create a cursor
        cursor = conn.cursor()
        
        # Check if columns already exist
        logger.info("Checking if columns already exist")
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'products' AND column_name IN ('features', 'specifications')
        """)
        existing_columns = [col[0] for col in cursor.fetchall()]
        
        # Add features column if it doesn't exist
        if 'features' not in existing_columns:
            logger.info("Adding features column to products table...")
            cursor.execute("""
                ALTER TABLE products 
                ADD COLUMN features JSONB
            """)
            logger.info("Features column added successfully.")
        else:
            logger.info("Features column already exists.")
        
        # Add specifications column if it doesn't exist
        if 'specifications' not in existing_columns:
            logger.info("Adding specifications column to products table...")
            cursor.execute("""
                ALTER TABLE products 
                ADD COLUMN specifications JSONB
            """)
            logger.info("Specifications column added successfully.")
        else:
            logger.info("Specifications column already exists.")
        
        # Close the cursor and connection
        cursor.close()
        conn.close()
        
        logger.info("Database schema update completed successfully.")
        return True
    
    except Exception as e:
        logger.error(f"Error updating database schema: {e}")
        return False

if __name__ == "__main__":
    add_columns()

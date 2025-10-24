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
    DATABASE_URL = "postgresql://postgres:npg_Y0WE8ibnFjge@azlok-shopping-private.cnack2uoelgc.ap-south-1.rds.amazonaws.com/azlok_shopping?sslmode=require&channel_binding=require"
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

def create_checkout_tables():
    """Create UserAddress, ShippingMethod, and PaymentMethod tables if they don't exist"""
    
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
        
        # Check if user_addresses table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'user_addresses'
            )
        """)
        user_addresses_exists = cursor.fetchone()[0]
        
        if not user_addresses_exists:
            logger.info("Creating user_addresses table...")
            cursor.execute("""
                CREATE TABLE user_addresses (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    full_name VARCHAR(255) NOT NULL,
                    address_line1 VARCHAR(255) NOT NULL,
                    address_line2 VARCHAR(255),
                    city VARCHAR(255) NOT NULL,
                    state VARCHAR(255) NOT NULL,
                    country VARCHAR(255) NOT NULL,
                    zip_code VARCHAR(20) NOT NULL,
                    phone_number VARCHAR(20) NOT NULL,
                    is_default BOOLEAN DEFAULT FALSE,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE
                )
            """)
            logger.info("user_addresses table created successfully")
        else:
            logger.info("user_addresses table already exists")
        
        # Check if shipping_methods table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'shipping_methods'
            )
        """)
        shipping_methods_exists = cursor.fetchone()[0]
        
        if not shipping_methods_exists:
            logger.info("Creating shipping_methods table...")
            cursor.execute("""
                CREATE TABLE shipping_methods (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    price FLOAT NOT NULL,
                    estimated_days VARCHAR(50) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE
                )
            """)
            
            # Insert default shipping methods
            cursor.execute("""
                INSERT INTO shipping_methods (name, description, price, estimated_days)
                VALUES 
                ('Standard Shipping', 'Delivery within 3-5 business days', 50.0, '3-5 days'),
                ('Express Shipping', 'Delivery within 1-2 business days', 100.0, '1-2 days'),
                ('Same Day Delivery', 'Delivery within 24 hours (select areas only)', 200.0, 'Same day')
            """)
            logger.info("shipping_methods table created and populated with default values")
        else:
            logger.info("shipping_methods table already exists")
        
        # Check if payment_methods table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'payment_methods'
            )
        """)
        payment_methods_exists = cursor.fetchone()[0]
        
        # Check if payment_method_type enum exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM pg_type
                WHERE typname = 'payment_method_type'
            )
        """)
        payment_method_type_exists = cursor.fetchone()[0]
        
        if not payment_method_type_exists:
            logger.info("Creating payment_method_type enum...")
            cursor.execute("""
                CREATE TYPE payment_method_type AS ENUM (
                    'credit_card', 'debit_card', 'upi', 'net_banking', 
                    'wallet', 'cash_on_delivery', 'emi', 'bank_transfer'
                )
            """)
            logger.info("payment_method_type enum created successfully")
        else:
            logger.info("payment_method_type enum already exists")
        
        if not payment_methods_exists:
            logger.info("Creating payment_methods table...")
            cursor.execute("""
                CREATE TABLE payment_methods (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    method_type payment_method_type,
                    provider VARCHAR(255),
                    is_default BOOLEAN DEFAULT FALSE,
                    is_active BOOLEAN DEFAULT TRUE,
                    last_used TIMESTAMP WITH TIME ZONE,
                    card_last_four VARCHAR(4),
                    card_expiry_month VARCHAR(2),
                    card_expiry_year VARCHAR(4),
                    card_holder_name VARCHAR(255),
                    upi_id VARCHAR(255),
                    bank_name VARCHAR(255),
                    account_last_four VARCHAR(4),
                    account_holder_name VARCHAR(255),
                    wallet_provider VARCHAR(255),
                    wallet_id VARCHAR(255),
                    token VARCHAR(255),
                    token_expiry TIMESTAMP WITH TIME ZONE,
                    payment_metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE
                )
            """)
            logger.info("payment_methods table created successfully")
        else:
            logger.info("payment_methods table already exists")
        
        # Close the connection
        cursor.close()
        conn.close()
        
        logger.info("All checkout tables created or verified successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error creating checkout tables: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting checkout tables creation script")
    success = create_checkout_tables()
    if success:
        logger.info("Checkout tables creation completed successfully")
    else:
        logger.error("Checkout tables creation failed")

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
    DATABASE_URL = "postgresql://postgres:npg_Y0WE8ibnFjge@proxy-1761299629688-azlok-shopping.proxy-cnack2uoelgc.ap-south-1.rds.amazonaws.com/azlok_shopping?sslmode=require&channel_binding=require"
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

def add_blog_tables():
    """Add blog tables to the database"""
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
        
        # Check if blogs table already exists
        logger.info("Checking if blogs table already exists")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'blogs'
            )
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            logger.info("Creating blogs table...")
            cursor.execute("""
                CREATE TABLE blogs (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    slug VARCHAR(255) UNIQUE NOT NULL,
                    content TEXT NOT NULL,
                    excerpt TEXT,
                    featured_image VARCHAR(255),
                    author_id INTEGER REFERENCES users(id),
                    status VARCHAR(20) DEFAULT 'draft',
                    published_date TIMESTAMP WITH TIME ZONE,
                    meta_title VARCHAR(255),
                    meta_description TEXT,
                    tags JSONB,
                    views_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE
                )
            """)
            logger.info("Blogs table created successfully.")
            
            # Create indexes for blogs table
            logger.info("Creating indexes for blogs table...")
            cursor.execute("CREATE INDEX idx_blogs_author_id ON blogs(author_id)")
            cursor.execute("CREATE INDEX idx_blogs_status ON blogs(status)")
            cursor.execute("CREATE INDEX idx_blogs_published_date ON blogs(published_date)")
            logger.info("Indexes created successfully.")
        else:
            logger.info("Blogs table already exists.")
        
        # Check if blog_product table already exists
        logger.info("Checking if blog_product table already exists")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'blog_product'
            )
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            logger.info("Creating blog_product table...")
            cursor.execute("""
                CREATE TABLE blog_product (
                    blog_id INTEGER REFERENCES blogs(id) ON DELETE CASCADE,
                    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
                    PRIMARY KEY (blog_id, product_id)
                )
            """)
            logger.info("Blog_product table created successfully.")
            
            # Create indexes for blog_product table
            logger.info("Creating indexes for blog_product table...")
            cursor.execute("CREATE INDEX idx_blog_product_blog_id ON blog_product(blog_id)")
            cursor.execute("CREATE INDEX idx_blog_product_product_id ON blog_product(product_id)")
            logger.info("Indexes created successfully.")
        else:
            logger.info("Blog_product table already exists.")
        
        # Close the cursor and connection
        cursor.close()
        conn.close()
        
        logger.info("Database schema update completed successfully.")
        return True
    
    except Exception as e:
        logger.error(f"Error updating database schema: {e}")
        return False

if __name__ == "__main__":
    add_blog_tables()

from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import redis
import time
import logging
import os

# Configure logging
logger = logging.getLogger(__name__)

# PostgreSQL connection string
DATABASE_URL = "postgresql://neondb_owner:npg_Y0WE8ibnFjge@ep-empty-glade-a1mnqsgm-pooler.ap-southeast-1.aws.neon.tech/azlok_shopping?sslmode=require&channel_binding=require"

# Redis connection
REDIS_URL = "redis://default:neXvrqBYXo5Hwdcbm3JBRCTYyuriDgSU@redis-11813.c323.us-east-1-2.ec2.redns.redis-cloud.com:11813"

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=5,  # Maximum number of connections to keep
    max_overflow=10,  # Maximum number of connections that can be created beyond pool_size
    pool_timeout=30,  # Timeout for getting a connection from the pool
    pool_recycle=1800,  # Recycle connections after 30 minutes
    pool_pre_ping=True,  # Test connections with a ping before using
    poolclass=QueuePool  # Use QueuePool for connection pooling
)

# Add event listeners for connection issues
@event.listens_for(engine, "connect")
def connect(dbapi_connection, connection_record):
    logger.info("Database connection established")

@event.listens_for(engine, "checkout")
def checkout(dbapi_connection, connection_record, connection_proxy):
    logger.debug("Database connection checked out from pool")

@event.listens_for(engine, "checkin")
def checkin(dbapi_connection, connection_record):
    logger.debug("Database connection returned to pool")

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Redis client
try:
    # Configure Redis with SSL support for rediss:// URLs
    ssl_enabled = REDIS_URL.startswith('rediss://')
    redis_client = redis.from_url(
        REDIS_URL, 
        decode_responses=True,
        socket_connect_timeout=5.0,
        ssl=ssl_enabled
    )
    # Test connection
    redis_client.ping()
    logger.info("Redis connection established successfully")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Caching will be disabled.")
    redis_client = None

# Dependency to get DB session with retry logic
def get_db():
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        db = SessionLocal()
        try:
            # Test the connection with proper text() wrapper
            db.execute(text("SELECT 1"))
            yield db
            break
        except Exception as e:
            db.close()
            if attempt < max_retries - 1:
                logger.warning(f"Database connection failed (attempt {attempt+1}/{max_retries}): {str(e)}")
                time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
            else:
                logger.error(f"Database connection failed after {max_retries} attempts: {str(e)}")
                raise
        finally:
            db.close()

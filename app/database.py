from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import redis

# PostgreSQL connection string
DATABASE_URL = "postgresql://neondb_owner:npg_Y0WE8ibnFjge@ep-empty-glade-a1mnqsgm-pooler.ap-southeast-1.aws.neon.tech/azlok_shopping?sslmode=require&channel_binding=require"

# Redis connection
REDIS_URL = "redis://red-d2hf7madbo4c73b07d80:6379"

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Redis client
redis_client = redis.from_url(REDIS_URL)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

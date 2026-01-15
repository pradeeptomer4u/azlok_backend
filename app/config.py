from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str = "postgresql://postgres:npg_Y0WE8ibnFjge@azlok-shopping.cnack2uoelgc.ap-south-1.rds.amazonaws.com/azlok_shopping?sslmode=require&channel_binding=require"


    # JWT settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # AWS settings
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION: Optional[str] = os.getenv("AWS_REGION", "ap-south-1")
    S3_BUCKET_NAME: Optional[str] = os.getenv("S3_BUCKET_NAME")

    # Redis settings
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Razorpay settings
    RAZORPAY_KEY_ID: str = "rzp_live_RUNzD6LppR2Rbc"
    RAZORPAY_KEY_SECRET: str = "QHjL1yzacXE1r8QOp7GNvHZr"
    RAZORPAY_WEBHOOK_SECRET: str = "dwGY4yAJufR6u6SK8lc"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

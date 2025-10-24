from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import Optional
import logging
import traceback

from .. import models, schemas
from ..database import get_db

logger = logging.getLogger(__name__)

# JWT settings
SECRET_KEY = "VJn8XqmoWSJZIZu6xQD6T4UfAtvgVnyO"  # In production, use a secure key and store in environment variables
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 3000000
# Password hashing
pwd_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")

router = APIRouter()

def verify_password(plain_password, hashed_password):
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError:
        # bcrypt backend throws ValueError when password > 72 bytes (or other backend issues).
        logger.warning("Password verification failed due to backend ValueError (possible >72 bytes).")
        return False
    except Exception:
        logger.exception("Unexpected error during password verification")
        return False

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(db: Session, username: str, password: str):
    # Try to find user by username first, then by email
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        user = db.query(models.User).filter(models.User.email == username).first()
    if not user:
        return False
    # Debug/log password length (bytes) — remove or lower log level in production
    try:
        pw_len = len(password.encode("utf-8"))
        logger.debug("Authenticating user=%s password bytes length=%d", username, pw_len)
    except Exception:
        logger.debug("Could not measure password byte length")

    if not verify_password(password, user.hashed_password):
        return False

    # If hash needs update (e.g., legacy bcrypt -> bcrypt_sha256), re-hash and persist
    try:
        if pwd_context.needs_update(user.hashed_password):
            logger.debug("Password hash for user %s needs update; re-hashing and saving.", user.username)
            new_hash = get_password_hash(password)
            user.hashed_password = new_hash
            db.add(user)
            db.commit()
            db.refresh(user)
    except Exception:
        # don't fail authentication if rehash fails; just log it
        logger.exception("Failed to re-hash or update password for user %s", user.username)

    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        logger.debug(f"Decoding token: {token[:20]}...")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.debug(f"Token payload: {payload}")
        username: str = payload.get("sub")
        if username is None:
            logger.warning("Username not found in token payload")
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
        logger.debug(f"Token data: {token_data}")
    except JWTError as e:
        logger.error(f"JWT Error: {str(e)}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Unexpected error in token validation: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

    try:
        logger.debug(f"Looking up user with username: {token_data.username}")
        user = db.query(models.User).filter(models.User.username == token_data.username).first()
        if user is None:
            logger.warning(f"User not found for username: {token_data.username}")
            raise credentials_exception
        logger.debug(f"Found user: {user.username}, ID: {user.id}, Role: {user.role}")
        return user
    except Exception as e:
        logger.error(f"Database error in get_current_user: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

async def get_current_active_user(current_user: schemas.User = Depends(get_current_user)):
    try:
        logger.debug(f"Checking if user {current_user.username} is active")
        if not current_user.is_active:
            logger.warning(f"User {current_user.username} is inactive")
            raise HTTPException(status_code=400, detail="Inactive user")
        logger.debug(f"User {current_user.username} is active, returning user data")
        return current_user
    except Exception as e:
        logger.error(f"Error in get_current_active_user: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

async def get_admin_user(current_user: schemas.User = Depends(get_current_active_user)):
    if current_user.role != models.UserRole.ADMIN and current_user.role != models.UserRole.COMPANY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin role required."
        )
    return current_user

async def get_seller_or_admin_user(current_user: schemas.User = Depends(get_current_active_user)):
    if current_user.role not in [models.UserRole.SELLER, models.UserRole.ADMIN, models.UserRole.COMPANY]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Seller or Admin role required."
        )
    return current_user

@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/check-username/{username}", response_model=schemas.UsernameAvailability)
async def check_username_availability(username: str, db: Session = Depends(get_db)):
    """
    Check if a username is available for registration
    """
    try:
        db_user = db.query(models.User).filter(models.User.username == username).first()
        is_available = db_user is None
        
        return {
            "username": username,
            "available": is_available,
            "message": "Username is available" if is_available else "Username is already taken"
        }
    except Exception as e:
        logger.error(f"Error checking username availability: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking username availability: {str(e)}"
        )

@router.post("/register", response_model=schemas.User)
async def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

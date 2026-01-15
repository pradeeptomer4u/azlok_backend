from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import Optional
import logging
import traceback
from .. import models, schemas
from ..database import get_db
import secrets
from ..utils.email_service import EmailService


logger = logging.getLogger(__name__)

# JWT settings
SECRET_KEY = "VJn8XqmoWSJZIZu6xQD6T4UfAtvgVnyO"  # In production, use a secure key and store in environment variables
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 3000000
# Password hashing
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    # These are strong Argon2 parameters
    argon2__time_cost=4,        # Number of iterations
    argon2__memory_cost=65536,  # 64MB memory usage
    argon2__parallelism=8,      # Degree of parallelism
    argon2__hash_len=32,        # Length of the hash in bytes
    argon2__salt_len=16,        # Length of the salt in bytes
    argon2__type="ID"           # Argon2id variant (most secure)
)
# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")

router = APIRouter()


def verify_password(plain_password, hashed_password):
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {str(e)}")
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
    if not verify_password(password, user.hashed_password):
        return False
    if pwd_context.needs_update(user.hashed_password):
        logger.info(f"Updating password hash for user {user.username}")
        user.hashed_password = get_password_hash(password)
        db.commit()
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


@router.post("/forgot-password", response_model=schemas.ForgotPasswordResponse)
async def forgot_password(
        request: schemas.ForgotPasswordRequest,
        db: Session = Depends(get_db)
):
    """
    Request a password reset token. Sends an email with reset link.
    """
    try:
        user = db.query(models.User).filter(models.User.email == request.email).first()

        if not user:
            return {"message": "If the email exists, a password reset link has been sent."}

        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        db.query(models.PasswordResetToken).filter(
            models.PasswordResetToken.user_id == user.id,
            models.PasswordResetToken.is_used == False
        ).update({"is_used": True})

        reset_token = models.PasswordResetToken(
            user_id=int(user.id),
            token=token,
            expires_at=expires_at
        )
        db.add(reset_token)
        db.commit()
        
        logger.info(f"Password reset token created for user {user.email}: {token[:20]}...")

        try:
            EmailService.send_password_reset_email_sync(
                recipient_email=str(user.email),
                reset_token=str(token),
                user_name=str(user.full_name or user.username)
            )
            logger.info(f"Password reset email sent successfully to {user.email}")
        except Exception as email_error:
            logger.error(f"Failed to send password reset email to {user.email}: {str(email_error)}")
            # Continue anyway - token is saved in DB

        return {"message": "If the email exists, a password reset link has been sent."}

    except Exception as e:
        logger.error(f"Error in forgot_password: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request."
        )


@router.post("/reset-password", response_model=schemas.ResetPasswordResponse)
async def reset_password(
        request: schemas.ResetPasswordRequest,
        db: Session = Depends(get_db)
):
    """
    Reset password using a valid reset token.
    """
    try:
        logger.info(f"Password reset attempt with token: {request.token[:20]}...")
        
        reset_token = db.query(models.PasswordResetToken).filter(
            models.PasswordResetToken.token == request.token,
            models.PasswordResetToken.is_used == False
        ).first()

        if not reset_token:
            logger.warning(f"Reset token not found or already used: {request.token[:20]}...")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token."
            )

        current_time = datetime.now(reset_token.expires_at.tzinfo) if reset_token.expires_at.tzinfo else datetime.utcnow()
        logger.info(f"Token found. Expires at: {reset_token.expires_at}, Current time: {current_time}")
        
        if reset_token.expires_at < current_time:
            logger.warning(f"Reset token has expired: {request.token[:20]}...")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired."
            )

        user = db.query(models.User).filter(models.User.id == reset_token.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )

        user.hashed_password = get_password_hash(request.new_password)
        reset_token.is_used = True

        db.commit()

        return {"message": "Password has been reset successfully."}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in reset_password: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting your password."
        )

@router.get("/debug/check-user/{email}")
async def debug_check_user(email: str, db: Session = Depends(get_db)):
    """Debug endpoint to check user authentication"""
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            return {"error": "User not found", "email": email}
        
        # Test with known password
        test_password = "0n3C0mp@ny"
        is_valid = verify_password(test_password, user.hashed_password)
        
        # Also test simple password
        simple_password = "admin123"
        is_valid_simple = verify_password(simple_password, user.hashed_password)
        
        return {
            "user_id": user.id,
            "email": user.email,
            "username": user.username,
            "is_active": user.is_active,
            "role": str(user.role),
            "hash_prefix": user.hashed_password[:40],
            "password_0n3C0mp@ny": "valid" if is_valid else "invalid",
            "password_admin123": "valid" if is_valid_simple else "invalid"
        }
    except Exception as e:
        logger.error(f"Debug check user error: {str(e)}")
        return {"error": str(e)}

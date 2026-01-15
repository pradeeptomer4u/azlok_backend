"""
Force update admin password and verify it works
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.database import DATABASE_URL
from app.models import User
from passlib.context import CryptContext
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def force_update_password():
    """Force update and verify password multiple times"""
    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        admin_email = "admin@azlok.com"
        new_password = "0n3C0mp@ny"
        
        print("\n" + "=" * 70)
        print("FORCE PASSWORD UPDATE FOR PRODUCTION")
        print("=" * 70)
        
        # Find user
        user = db.query(User).filter(User.email == admin_email).first()
        if not user:
            print(f"ERROR: User {admin_email} not found!")
            return False
        
        print(f"\nUser found:")
        print(f"  ID: {user.id}")
        print(f"  Email: {user.email}")
        print(f"  Username: {user.username}")
        print(f"  Current hash: {user.hashed_password[:50]}...")
        
        # Generate new hash
        print(f"\nGenerating new hash for password: {new_password}")
        new_hash = pwd_context.hash(new_password)
        print(f"  New hash: {new_hash[:50]}...")
        
        # Update password
        print(f"\nUpdating password in database...")
        user.hashed_password = new_hash
        db.commit()
        print(f"  ✓ Committed to database")
        
        # Verify immediately by querying again
        print(f"\nVerifying update (fresh query)...")
        db.expire_all()  # Clear session cache
        user_fresh = db.query(User).filter(User.email == admin_email).first()
        
        print(f"  Fresh hash from DB: {user_fresh.hashed_password[:50]}...")
        print(f"  Hashes match: {user_fresh.hashed_password == new_hash}")
        
        # Test password verification
        print(f"\nTesting password verification...")
        is_valid = pwd_context.verify(new_password, user_fresh.hashed_password)
        print(f"  Password '{new_password}' is: {'✓ VALID' if is_valid else '✗ INVALID'}")
        
        if not is_valid:
            print(f"\n  ERROR: Password verification failed!")
            print(f"  This should not happen. Trying one more time...")
            
            # Try again with a fresh hash
            new_hash2 = pwd_context.hash(new_password)
            user_fresh.hashed_password = new_hash2
            db.commit()
            
            db.expire_all()
            user_final = db.query(User).filter(User.email == admin_email).first()
            is_valid_final = pwd_context.verify(new_password, user_final.hashed_password)
            print(f"  Second attempt: {'✓ VALID' if is_valid_final else '✗ INVALID'}")
        
        # Test authentication flow
        print(f"\n" + "=" * 70)
        print("TESTING AUTHENTICATION FLOW")
        print("=" * 70)
        
        # Test 1: Find by email
        print(f"\n1. Finding user by email '{admin_email}'...")
        user_by_email = db.query(User).filter(User.email == admin_email).first()
        if user_by_email:
            print(f"   ✓ Found: {user_by_email.username}")
            is_valid_email = pwd_context.verify(new_password, user_by_email.hashed_password)
            print(f"   Password valid: {'✓ YES' if is_valid_email else '✗ NO'}")
        
        # Test 2: Find by username
        print(f"\n2. Finding user by username '{user.username}'...")
        user_by_username = db.query(User).filter(User.username == user.username).first()
        if user_by_username:
            print(f"   ✓ Found: {user_by_username.email}")
            is_valid_username = pwd_context.verify(new_password, user_by_username.hashed_password)
            print(f"   Password valid: {'✓ YES' if is_valid_username else '✗ NO'}")
        
        # Test 3: Simulate authenticate_user
        print(f"\n3. Simulating authenticate_user function...")
        test_user = db.query(User).filter(User.username == admin_email).first()
        if not test_user:
            test_user = db.query(User).filter(User.email == admin_email).first()
        
        if test_user:
            print(f"   ✓ User found: {test_user.email}")
            print(f"   Is active: {test_user.is_active}")
            auth_valid = pwd_context.verify(new_password, test_user.hashed_password)
            print(f"   Password valid: {'✓ YES' if auth_valid else '✗ NO'}")
            
            if auth_valid:
                print(f"\n   *** AUTHENTICATION SHOULD WORK! ***")
            else:
                print(f"\n   *** AUTHENTICATION WILL FAIL! ***")
        
        db.close()
        return is_valid
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = force_update_password()
    
    print("\n" + "=" * 70)
    if success:
        print("PASSWORD UPDATE SUCCESSFUL")
        print("\nCredentials:")
        print("  Email: admin@azlok.com")
        print("  Username: azlok_admin")
        print("  Password: 0n3C0mp@ny")
        print("\nThe production server should now accept these credentials.")
    else:
        print("PASSWORD UPDATE FAILED")
        print("Check error messages above.")
    print("=" * 70)

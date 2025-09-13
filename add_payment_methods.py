#!/usr/bin/env python3
"""
Script to add default payment methods to the database
"""
import sys
import os
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app.models import PaymentMethod, PaymentMethodType

def add_default_payment_methods():
    """Add default payment methods to the database"""
    db = SessionLocal()
    try:
        # Check if Cash on Delivery payment method already exists
        existing_cod = db.query(PaymentMethod).filter(
            PaymentMethod.method_type == PaymentMethodType.COD,
            PaymentMethod.provider == "Cash on Delivery"
        ).first()
        
        if not existing_cod:
            # Add Cash on Delivery payment method
            cod_payment_method = PaymentMethod(
                user_id=None,  # System-wide payment method, not tied to a specific user
                method_type=PaymentMethodType.COD,
                provider="Cash on Delivery",
                is_default=True,
                is_active=True
            )
            db.add(cod_payment_method)
            db.commit()
            print("Cash on Delivery payment method added successfully")
        else:
            print("Cash on Delivery payment method already exists")
            
        # You can add more default payment methods here if needed
        
    except IntegrityError as e:
        db.rollback()
        print(f"Error adding payment methods: {e}")
    except Exception as e:
        db.rollback()
        print(f"Unexpected error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    add_default_payment_methods()
    print("Payment methods setup complete")

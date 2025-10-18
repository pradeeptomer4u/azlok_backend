from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from pydantic import BaseModel

from ..database import get_db
from ..utils.razorpay_utils import create_razorpay_order
from .auth import get_current_active_user
from ..schemas import User

router = APIRouter(
    prefix="/razorpay",
    tags=["razorpay"],
    responses={404: {"description": "Not found"}},
)


class RazorpayOrderRequest(BaseModel):
    amount: float
    currency: str = "INR"
    receipt: Optional[str] = None
    notes: Optional[Dict[str, str]] = None


@router.post("/create-order", status_code=status.HTTP_200_OK)
async def create_order(
        order_request: RazorpayOrderRequest,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """
    Create a new Razorpay order
    """
    try:
        # Create order in Razorpay
        order = create_razorpay_order(
            amount=order_request.amount,
            currency=order_request.currency,
            receipt=order_request.receipt,
            notes=order_request.notes
        )

        return order
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create Razorpay order: {str(e)}"
        )


class RazorpayVerificationRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


@router.post("/verify-payment", status_code=status.HTTP_200_OK)
async def verify_payment(
        verification_request: RazorpayVerificationRequest,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """
    Verify a Razorpay payment signature
    """
    try:
        from ..utils.razorpay_utils import verify_payment_signature

        # Verify the payment signature
        is_valid = verify_payment_signature(
            razorpay_order_id=verification_request.razorpay_order_id,
            razorpay_payment_id=verification_request.razorpay_payment_id,
            razorpay_signature=verification_request.razorpay_signature
        )

        if is_valid:
            # If you want to update order status or create payment records,
            # you can do that here

            return {"verified": True}
        else:
            return {"verified": False}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify payment: {str(e)}"
        )
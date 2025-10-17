from fastapi import APIRouter, Depends, HTTPException, status, Request, Header, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
import hmac
import hashlib
import razorpay
import json
from typing import Dict, Any

from ..database import get_db
from ..models import Payment, Transaction, PaymentStatus, TransactionType, Order, OrderStatus
from ..config import settings

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

router = APIRouter(
    prefix="/razorpay",
    tags=["razorpay"],
    responses={404: {"description": "Not found"}},
)

def generate_transaction_reference():
    """Generate a unique transaction reference"""
    from uuid import uuid4
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = str(uuid4().hex)[:8]
    return f"TXN-{timestamp}-{unique_id}"

@router.post("/webhook", status_code=status.HTTP_200_OK)
async def razorpay_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_razorpay_signature: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Webhook endpoint for Razorpay payment callbacks.
    This endpoint receives notifications about payment status changes.
    """
    # Get the raw request body
    body = await request.body()
    body_text = body.decode("utf-8")

    # Verify webhook signature
    if settings.RAZORPAY_WEBHOOK_SECRET:
        is_valid = verify_webhook_signature(body_text, x_razorpay_signature, settings.RAZORPAY_WEBHOOK_SECRET)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature"
            )

    # Parse the webhook payload
    payload = await request.json()

    # Process the webhook event in the background to avoid timeout
    background_tasks.add_task(process_razorpay_webhook, payload, db)

    # Return a success response immediately
    return {"status": "received"}


def verify_webhook_signature(body_text: str, signature: str, webhook_secret: str) -> bool:
    """
    Verify the Razorpay webhook signature to ensure the request is legitimate.
    """
    if not signature or not webhook_secret:
        return False

    expected_signature = hmac.new(
        key=webhook_secret.encode(),
        msg=body_text.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)


async def process_razorpay_webhook(payload: Dict[str, Any], db: Session):
    """
    Process Razorpay webhook events and update payment/order status accordingly.
    """
    event = payload.get("event")

    # Handle different event types
    if event == "payment.authorized":
        await handle_payment_authorized(payload, db)
    elif event == "payment.captured":
        await handle_payment_captured(payload, db)
    elif event == "payment.failed":
        await handle_payment_failed(payload, db)
    elif event == "refund.processed":
        await handle_refund_processed(payload, db)
    # Add more event handlers as needed


async def handle_payment_authorized(payload: Dict[str, Any], db: Session):
    """
    Handle payment.authorized event from Razorpay.
    This event is triggered when a payment is authorized but not yet captured.
    """
    payment_data = payload.get("payload", {}).get("payment", {}).get("entity", {})
    razorpay_payment_id = payment_data.get("id")

    # Find the payment in our database
    payment = db.query(Payment).filter(
        Payment.gateway == "razorpay",
        Payment.gateway_payment_id == razorpay_payment_id
    ).first()

    if payment:
        # Update payment status
        payment.status = PaymentStatus.PENDING
        payment.gateway_response = payment_data
        db.commit()


async def handle_payment_captured(payload: Dict[str, Any], db: Session):
    """
    Handle payment.captured event from Razorpay.
    This event is triggered when a payment is successfully captured.
    """
    payment_data = payload.get("payload", {}).get("payment", {}).get("entity", {})
    razorpay_payment_id = payment_data.get("id")
    order_id = payment_data.get("notes", {}).get("order_id")

    # Find the payment in our database
    payment = db.query(Payment).filter(
        Payment.gateway == "razorpay",
        Payment.gateway_payment_id == razorpay_payment_id
    ).first()

    if payment:
        # Update payment status
        payment.status = PaymentStatus.PAID
        payment.payment_date = datetime.now()
        payment.gateway_response = payment_data
        db.commit()

        # Update order status if order_id exists
        if payment.order_id:
            order = db.query(Order).filter(Order.id == payment.order_id).first()
            if order:
                order.payment_status = PaymentStatus.PAID
                if order.status == OrderStatus.PENDING:
                    order.status = OrderStatus.PROCESSING
                db.commit()

    # If payment not found but order_id is in notes, try to find by order
    elif order_id:
        try:
            order_id_int = int(order_id)
            order = db.query(Order).filter(Order.id == order_id_int).first()
            if order:
                # Create a new payment record
                new_payment = Payment(
                    payment_reference=f"RZP-{razorpay_payment_id}",
                    order_id=order.id,
                    user_id=order.user_id,
                    amount=float(payment_data.get("amount", 0)) / 100,  # Convert from paise to rupees
                    currency=payment_data.get("currency", "INR"),
                    status=PaymentStatus.PAID,
                    payment_date=datetime.now(),
                    gateway="razorpay",
                    gateway_payment_id=razorpay_payment_id,
                    gateway_response=payment_data
                )
                db.add(new_payment)

                # Update order status
                order.payment_status = PaymentStatus.PAID
                if order.status == OrderStatus.PENDING:
                    order.status = OrderStatus.PROCESSING

                db.commit()
        except (ValueError, TypeError):
            # Log error: order_id is not a valid integer
            pass


async def handle_payment_failed(payload: Dict[str, Any], db: Session):
    """
    Handle payment.failed event from Razorpay.
    This event is triggered when a payment fails.
    """
    payment_data = payload.get("payload", {}).get("payment", {}).get("entity", {})
    razorpay_payment_id = payment_data.get("id")

    # Find the payment in our database
    payment = db.query(Payment).filter(
        Payment.gateway == "razorpay",
        Payment.gateway_payment_id == razorpay_payment_id
    ).first()

    if payment:
        # Update payment status
        payment.status = PaymentStatus.FAILED
        payment.gateway_response = payment_data
        db.commit()

        # Update order status if order_id exists
        if payment.order_id:
            order = db.query(Order).filter(Order.id == payment.order_id).first()
            if order:
                order.payment_status = PaymentStatus.FAILED
                db.commit()


async def handle_refund_processed(payload: Dict[str, Any], db: Session):
    """
    Handle refund.processed event from Razorpay.
    This event is triggered when a refund is processed.
    """
    refund_data = payload.get("payload", {}).get("refund", {}).get("entity", {})
    razorpay_payment_id = refund_data.get("payment_id")
    refund_amount = float(refund_data.get("amount", 0)) / 100  # Convert from paise to rupees

    # Find the payment in our database
    payment = db.query(Payment).filter(
        Payment.gateway == "razorpay",
        Payment.gateway_payment_id == razorpay_payment_id
    ).first()

    if payment:
        # Update payment refund status
        payment.refunded_amount = refund_amount

        # If fully refunded, update status
        if payment.refunded_amount >= payment.amount:
            payment.status = PaymentStatus.REFUNDED

        payment.gateway_response = {**payment.gateway_response, "refund": refund_data} if payment.gateway_response else {"refund": refund_data}
        db.commit()

        # Create refund transaction
        transaction_reference = generate_transaction_reference()
        db_transaction = Transaction(
            transaction_reference=transaction_reference,
            payment_id=payment.id,
            user_id=payment.user_id,
            transaction_type=TransactionType.REFUND,
            amount=refund_amount,
            currency=payment.currency,
            status="success",
            description=f"Refund processed via Razorpay for payment {payment.payment_reference}",
            transaction_date=datetime.now()
        )

        db.add(db_transaction)
        db.commit()

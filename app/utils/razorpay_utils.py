import razorpay
from typing import Dict, Any, Optional
from ..config import settings

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def create_razorpay_order(
    amount: float,
    currency: str = "INR",
    receipt: Optional[str] = None,
    notes: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Create a new Razorpay order

    Args:
        amount: Amount in rupees (will be converted to paise)
        currency: Currency code (default: INR)
        receipt: Receipt ID (optional)
        notes: Additional notes for the order (optional)

    Returns:
        Dictionary containing Razorpay order details
    """
    # Convert amount to paise (Razorpay uses smallest currency unit)
    amount_in_paise = int(amount * 100)

    # Prepare order data
    data = {
        "amount": amount_in_paise,
        "currency": currency,
    }

    if receipt:
        data["receipt"] = receipt

    if notes:
        data["notes"] = notes

    # Create order in Razorpay
    try:
        order = razorpay_client.order.create(data=data)
        return order
    except Exception as e:
        # Log the error
        print(f"Error creating Razorpay order: {str(e)}")
        raise

def verify_payment_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str
) -> bool:
    """
    Verify the payment signature to ensure the payment is legitimate

    Args:
        razorpay_order_id: Razorpay Order ID
        razorpay_payment_id: Razorpay Payment ID
        razorpay_signature: Signature received from Razorpay

    Returns:
        Boolean indicating if the signature is valid
    """
    try:
        return razorpay_client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        })
    except Exception:
        return False

def fetch_payment_details(payment_id: str) -> Dict[str, Any]:
    """
    Fetch payment details from Razorpay

    Args:
        payment_id: Razorpay Payment ID

    Returns:
        Dictionary containing payment details
    """
    try:
        return razorpay_client.payment.fetch(payment_id)
    except Exception as e:
        # Log the error
        print(f"Error fetching payment details: {str(e)}")
        raise

def capture_payment(payment_id: str, amount: float, currency: str = "INR") -> Dict[str, Any]:
    """
    Capture an authorized payment

    Args:
        payment_id: Razorpay Payment ID
        amount: Amount to capture in rupees (will be converted to paise)
        currency: Currency code (default: INR)

    Returns:
        Dictionary containing captured payment details
    """
    # Convert amount to paise
    amount_in_paise = int(amount * 100)

    try:
        return razorpay_client.payment.capture(payment_id, amount_in_paise, {"currency": currency})
    except Exception as e:
        # Log the error
        print(f"Error capturing payment: {str(e)}")
        raise

def refund_payment(
    payment_id: str,
    amount: Optional[float] = None,
    notes: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Refund a payment

    Args:
        payment_id: Razorpay Payment ID
        amount: Amount to refund in rupees (will be converted to paise). If None, full amount is refunded.
        notes: Additional notes for the refund (optional)

    Returns:
        Dictionary containing refund details
    """
    data = {}

    if amount:
        # Convert amount to paise
        amount_in_paise = int(amount * 100)
        data["amount"] = amount_in_paise

    if notes:
        data["notes"] = notes

    try:
        return razorpay_client.payment.refund(payment_id, data)
    except Exception as e:
        # Log the error
        print(f"Error refunding payment: {str(e)}")
        raise

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid

from ..database import get_db
from ..models import Payment, PaymentMethod, Transaction, InstallmentPlan, PaymentStatus, PaymentMethodType, TransactionType
from ..schemas import (
    PaymentCreate, PaymentUpdate, Payment as PaymentSchema, 
    PaymentMethodCreate, PaymentMethodUpdate,
    TransactionCreate, Transaction as TransactionSchema,
    InstallmentPlanCreate, InstallmentPlan as InstallmentPlanSchema,
    PaymentListResponse, PaymentSummary
)
from .payment_methods import PaymentMethodResponse
from .auth import get_current_active_user
from ..schemas import User

router = APIRouter()


# Helper functions
def generate_payment_reference():
    """Generate a unique payment reference"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = str(uuid.uuid4().hex)[:8]
    return f"PAY-{timestamp}-{unique_id}"

def generate_transaction_reference():
    """Generate a unique transaction reference"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = str(uuid.uuid4().hex)[:8]
    return f"TXN-{timestamp}-{unique_id}"

# Payment Methods Endpoints
@router.post("/methods", response_model=PaymentMethodResponse, status_code=status.HTTP_201_CREATED)
def create_payment_method(
    payment_method: PaymentMethodCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new payment method for the current user"""
    # Check if this is set as default
    if payment_method.is_default:
        # Set all other payment methods as non-default
        db.query(PaymentMethod).filter(
            PaymentMethod.user_id == current_user.id,
            PaymentMethod.is_default == True
        ).update({"is_default": False})
    
    # Create new payment method
    db_payment_method = PaymentMethod(
        user_id=current_user.id,
        method_type=payment_method.method_type,
        provider=payment_method.provider,
        is_default=payment_method.is_default,
        is_active=True,
        # Card details
        card_last_four=payment_method.card_last_four,
        card_expiry_month=payment_method.card_expiry_month,
        card_expiry_year=payment_method.card_expiry_year,
        card_holder_name=payment_method.card_holder_name,
        # UPI details
        upi_id=payment_method.upi_id,
        # Bank details
        bank_name=payment_method.bank_name,
        account_last_four=payment_method.account_last_four,
        account_holder_name=payment_method.account_holder_name,
        # Wallet details
        wallet_provider=payment_method.wallet_provider,
        wallet_id=payment_method.wallet_id
    )
    
    db.add(db_payment_method)
    db.commit()
    db.refresh(db_payment_method)
    return db_payment_method

@router.get("/methods", response_model=List[PaymentMethodResponse])
def get_payment_methods(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    active_only: bool = Query(True, description="Only return active payment methods")
):
    """Get all payment methods for the current user"""
    query = db.query(PaymentMethod).filter(PaymentMethod.user_id == current_user.id)
    
    if active_only:
        query = query.filter(PaymentMethod.is_active == True)
    
    return query.all()

@router.get("/methods/{payment_method_id}", response_model=PaymentMethodResponse)
def get_payment_method(
    payment_method_id: int = Path(..., description="The ID of the payment method to get"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific payment method by ID"""
    payment_method = db.query(PaymentMethod).filter(
        PaymentMethod.id == payment_method_id,
        PaymentMethod.user_id == current_user.id
    ).first()
    
    if not payment_method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found"
        )
    
    return payment_method

@router.put("/methods/{payment_method_id}", response_model=PaymentMethodResponse)
def update_payment_method(
    payment_method_update: PaymentMethodUpdate,
    payment_method_id: int = Path(..., description="The ID of the payment method to update"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a payment method"""
    payment_method = db.query(PaymentMethod).filter(
        PaymentMethod.id == payment_method_id,
        PaymentMethod.user_id == current_user.id
    ).first()
    
    if not payment_method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found"
        )
    
    # Check if setting as default
    if payment_method_update.is_default:
        # Set all other payment methods as non-default
        db.query(PaymentMethod).filter(
            PaymentMethod.user_id == current_user.id,
            PaymentMethod.is_default == True,
            PaymentMethod.id != payment_method_id
        ).update({"is_default": False})
    
    # Update payment method fields
    update_data = payment_method_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(payment_method, key, value)
    
    db.commit()
    db.refresh(payment_method)
    return payment_method

@router.delete("/methods/{payment_method_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment_method(
    payment_method_id: int = Path(..., description="The ID of the payment method to delete"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete (deactivate) a payment method"""
    payment_method = db.query(PaymentMethod).filter(
        PaymentMethod.id == payment_method_id,
        PaymentMethod.user_id == current_user.id
    ).first()
    
    if not payment_method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found"
        )
    
    # Instead of deleting, just mark as inactive
    payment_method.is_active = False
    db.commit()
    
    return None

# Payments Endpoints
@router.post("", response_model=PaymentSchema, status_code=status.HTTP_201_CREATED)
def create_payment(
    payment: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new payment"""
    # Generate payment reference
    payment_reference = generate_payment_reference()
    
    # Create payment
    db_payment = Payment(
        payment_reference=payment_reference,
        order_id=payment.order_id,
        user_id=current_user.id,
        payment_method_id=payment.payment_method_id,
        amount=payment.amount,
        currency=payment.currency,
        status=PaymentStatus.PENDING,
        description=payment.description,
        due_date=payment.due_date,
        gateway=payment.gateway,
        is_installment=payment.is_installment,
        installment_plan_id=payment.installment_plan_id,
        installment_number=payment.installment_number,
        is_recurring=payment.is_recurring,
        recurring_schedule=payment.recurring_schedule,
        refunded_amount=0.0,
        metadata=payment.metadata
    )
    
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    
    # Create initial transaction record
    transaction_reference = generate_transaction_reference()
    db_transaction = Transaction(
        transaction_reference=transaction_reference,
        payment_id=db_payment.id,
        user_id=current_user.id,
        transaction_type=TransactionType.PAYMENT,
        amount=payment.amount,
        currency=payment.currency,
        status="pending",
        gateway=payment.gateway,
        description=f"Initial payment transaction for {payment_reference}",
        metadata=payment.metadata
    )
    
    db.add(db_transaction)
    db.commit()
    
    # Update payment method last_used timestamp if provided
    if payment.payment_method_id:
        payment_method = db.query(PaymentMethod).filter(
            PaymentMethod.id == payment.payment_method_id
        ).first()
        if payment_method:
            payment_method.last_used = datetime.now()
            db.commit()
    
    return db_payment

@router.get("", response_model=PaymentListResponse)
def get_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    status: Optional[PaymentStatus] = Query(None, description="Filter by payment status"),
    order_id: Optional[int] = Query(None, description="Filter by order ID"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size")
):
    """Get all payments for the current user with pagination and filtering"""
    # Base query
    query = db.query(Payment).filter(Payment.user_id == current_user.id)
    
    # Apply filters
    if status:
        query = query.filter(Payment.status == status)
    
    if order_id:
        query = query.filter(Payment.order_id == order_id)
    
    if start_date:
        query = query.filter(Payment.created_at >= start_date)
    
    if end_date:
        query = query.filter(Payment.created_at <= end_date)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    payments = query.order_by(Payment.created_at.desc()).offset((page - 1) * size).limit(size).all()
    
    # Calculate total pages
    pages = (total + size - 1) // size
    
    return {
        "payments": payments,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages
    }

@router.get("/summary", response_model=PaymentSummary)
def get_payment_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date")
):
    """Get a summary of payments for the current user"""
    # Base query
    query = db.query(Payment).filter(Payment.user_id == current_user.id)
    
    # Apply date filters if provided
    if start_date:
        query = query.filter(Payment.created_at >= start_date)
    
    if end_date:
        query = query.filter(Payment.created_at <= end_date)
    
    # Get all relevant payments
    payments = query.all()
    
    # Calculate summary statistics
    total_payments = len(payments)
    total_amount = sum(payment.amount for payment in payments)
    paid_amount = sum(payment.amount for payment in payments if payment.status == PaymentStatus.PAID)
    pending_amount = sum(payment.amount for payment in payments if payment.status == PaymentStatus.PENDING)
    refunded_amount = sum(payment.refunded_amount for payment in payments)
    failed_amount = sum(payment.amount for payment in payments if payment.status == PaymentStatus.FAILED)
    
    # Count by status
    status_counts = {}
    for status_enum in PaymentStatus:
        status_counts[status_enum.value] = sum(1 for payment in payments if payment.status == status_enum)
    
    # Get recent payments
    recent_payments = query.order_by(Payment.created_at.desc()).limit(5).all()
    
    return {
        "total_payments": total_payments,
        "total_amount": total_amount,
        "paid_amount": paid_amount,
        "pending_amount": pending_amount,
        "refunded_amount": refunded_amount,
        "failed_amount": failed_amount,
        "currency": "INR",  # Default currency
        "payment_status_counts": status_counts,
        "recent_payments": recent_payments
    }

@router.get("/{payment_id}", response_model=PaymentSchema)
def get_payment(
    payment_id: int = Path(..., description="The ID of the payment to get"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific payment by ID"""
    payment = db.query(Payment).filter(
        Payment.id == payment_id,
        Payment.user_id == current_user.id
    ).first()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    return payment

@router.put("/{payment_id}", response_model=PaymentSchema)
def update_payment(
    payment_update: PaymentUpdate,
    payment_id: int = Path(..., description="The ID of the payment to update"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a payment (admin or seller only)"""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    # Only allow the payment owner or admin to update
    if payment.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this payment"
        )
    
    # Update payment fields
    update_data = payment_update.dict(exclude_unset=True)
    
    # Special handling for status changes
    old_status = payment.status
    new_status = update_data.get("status")
    
    if new_status and old_status != new_status:
        # Create a transaction record for status change
        transaction_reference = generate_transaction_reference()
        
        # Determine transaction type based on status change
        transaction_type = TransactionType.PAYMENT
        if new_status == PaymentStatus.REFUNDED:
            transaction_type = TransactionType.REFUND
        
        db_transaction = Transaction(
            transaction_reference=transaction_reference,
            payment_id=payment.id,
            user_id=current_user.id,
            transaction_type=transaction_type,
            amount=payment.amount,
            currency=payment.currency,
            status="success" if new_status in [PaymentStatus.PAID, PaymentStatus.REFUNDED] else "pending",
            description=f"Payment status changed from {old_status} to {new_status}",
            transaction_date=datetime.now()
        )
        
        db.add(db_transaction)
    
    # Apply updates
    for key, value in update_data.items():
        setattr(payment, key, value)
    
    # If payment is marked as paid, set payment_date
    if new_status == PaymentStatus.PAID and not payment.payment_date:
        payment.payment_date = datetime.now()
    
    db.commit()
    db.refresh(payment)
    return payment

@router.post("/{payment_id}/refund", response_model=PaymentSchema)
def refund_payment(
    payment_id: int = Path(..., description="The ID of the payment to refund"),
    amount: float = Query(..., description="Amount to refund"),
    reason: str = Query(None, description="Reason for refund"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Process a refund for a payment (admin only)"""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    # Validate refund amount
    if amount <= 0 or amount > (payment.amount - payment.refunded_amount):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid refund amount. Maximum refundable amount is {payment.amount - payment.refunded_amount}"
        )
    
    # Update payment
    payment.refunded_amount += amount
    payment.refund_reason = reason
    
    # If fully refunded, update status
    if payment.refunded_amount >= payment.amount:
        payment.status = PaymentStatus.REFUNDED
    
    # Create refund transaction
    transaction_reference = generate_transaction_reference()
    db_transaction = Transaction(
        transaction_reference=transaction_reference,
        payment_id=payment.id,
        user_id=current_user.id,
        transaction_type=TransactionType.REFUND,
        amount=amount,
        currency=payment.currency,
        status="success",
        description=f"Refund of {amount} {payment.currency} for payment {payment.payment_reference}. Reason: {reason}",
        transaction_date=datetime.now()
    )
    
    db.add(db_transaction)
    db.commit()
    db.refresh(payment)
    
    return payment

# Installment Plan Endpoints
@router.post("/installment-plans", response_model=InstallmentPlanSchema, status_code=status.HTTP_201_CREATED)
def create_installment_plan(
    plan: InstallmentPlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new installment plan"""
    # Create installment plan
    db_plan = InstallmentPlan(
        order_id=plan.order_id,
        user_id=current_user.id,
        total_amount=plan.total_amount,
        number_of_installments=plan.number_of_installments,
        installment_frequency=plan.installment_frequency,
        interest_rate=plan.interest_rate,
        processing_fee=plan.processing_fee,
        start_date=plan.start_date,
        status="active"
    )
    
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    
    return db_plan

@router.get("/installment-plans", response_model=List[InstallmentPlanSchema])
def get_installment_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    status: Optional[str] = Query(None, description="Filter by plan status")
):
    """Get all installment plans for the current user"""
    query = db.query(InstallmentPlan).filter(InstallmentPlan.user_id == current_user.id)
    
    if status:
        query = query.filter(InstallmentPlan.status == status)
    
    return query.all()

@router.get("/installment-plans/{plan_id}", response_model=InstallmentPlanSchema)
def get_installment_plan(
    plan_id: int = Path(..., description="The ID of the installment plan to get"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific installment plan by ID"""
    plan = db.query(InstallmentPlan).filter(
        InstallmentPlan.id == plan_id,
        InstallmentPlan.user_id == current_user.id
    ).first()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Installment plan not found"
        )
    
    return plan

# Transaction Endpoints
@router.get("/transactions", response_model=List[TransactionSchema])
def get_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    payment_id: Optional[int] = Query(None, description="Filter by payment ID"),
    transaction_type: Optional[TransactionType] = Query(None, description="Filter by transaction type"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date")
):
    """Get all transactions for the current user"""
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)
    
    if payment_id:
        query = query.filter(Transaction.payment_id == payment_id)
    
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)
    
    if start_date:
        query = query.filter(Transaction.transaction_date >= start_date)
    
    if end_date:
        query = query.filter(Transaction.transaction_date <= end_date)
    
    return query.order_by(Transaction.transaction_date.desc()).all()

@router.get("/transactions/{transaction_id}", response_model=TransactionSchema)
def get_transaction(
    transaction_id: int = Path(..., description="The ID of the transaction to get"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific transaction by ID"""
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    return transaction

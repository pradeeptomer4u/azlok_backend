from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import json
import uuid
import os
import shutil
from pathlib import Path

from .. import models, schemas, database, utils
from ..database import get_db
from .auth import get_current_user
from ..utils.pdf_generator import pdf_generator

router = APIRouter(
    prefix="/invoices",
    tags=["invoices"],
    responses={404: {"description": "Not found"}},
)

# Create invoice from order
@router.post("/generate/{order_id}", response_model=schemas.InvoiceResponse)
def generate_invoice(
    order_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Check if order exists
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if user is authorized (either the buyer or a seller of items in the order)
    if order.user_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        # Check if current user is a seller of any items in this order
        seller_item = db.query(models.OrderItem).filter(
            models.OrderItem.order_id == order_id,
            models.OrderItem.seller_id == current_user.id
        ).first()
        
        if not seller_item:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to generate invoice for this order"
            )
    
    # Check if invoice already exists for this order
    existing_invoice = db.query(models.Invoice).filter(
        models.Invoice.order_id == order_id
    ).first()
    
    if existing_invoice:
        return existing_invoice
    
    # Generate invoice number
    invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    
    # Create invoice
    new_invoice = models.Invoice(
        invoice_number=invoice_number,
        order_id=order_id,
        user_id=order.user_id,
        # For B2C, we don't need a specific seller_id as it's the platform selling to consumers
        # seller_id can be set for B2B scenarios where specific sellers fulfill orders
        
        # Set due date to 15 days from now
        due_date=datetime.now() + timedelta(days=15),
        status=models.InvoiceStatus.ISSUED,
        
        # Financial details from order
        subtotal=order.subtotal_amount,
        tax_amount=order.tax_amount,
        cgst_amount=order.cgst_amount,
        sgst_amount=order.sgst_amount,
        igst_amount=order.igst_amount,
        discount_amount=order.discount_amount,
        shipping_amount=order.shipping_amount,
        total_amount=order.total_amount,
        amount_paid=0.0 if order.payment_status == models.PaymentStatus.PENDING else order.total_amount,
        amount_due=order.total_amount if order.payment_status == models.PaymentStatus.PENDING else 0.0,
        
        # Address details
        billing_address=order.billing_address,
        shipping_address=order.shipping_address,
        
        # Additional details
        notes="Thank you for shopping with us!",
        terms="All sales are final. Returns accepted within 30 days with receipt.",
        payment_instructions="Please pay within 15 days of invoice date."
    )
    
    db.add(new_invoice)
    db.commit()
    db.refresh(new_invoice)
    
    # Create invoice line items from order items
    order_items = db.query(models.OrderItem).filter(models.OrderItem.order_id == order_id).all()
    
    for item in order_items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        
        line_item = models.InvoiceLineItem(
            invoice_id=new_invoice.id,
            product_id=item.product_id,
            description=product.name if product else "Product",
            quantity=item.quantity,
            unit_price=item.price,
            tax_rate=item.tax_amount / (item.price * item.quantity) * 100 if item.tax_amount > 0 else 0.0,
            tax_amount=item.tax_amount,
            total=item.total,
            hsn_code=product.hsn_code if product else None
        )
        
        db.add(line_item)
    
    # Update order with invoice number
    order.invoice_number = invoice_number
    order.invoice_date = datetime.now()
    
    db.commit()
    
    # Generate PDF invoice in background
    background_tasks.add_task(generate_invoice_pdf, new_invoice.id, db)
    
    return new_invoice


# Get all invoices for current user
@router.get("/", response_model=List[schemas.InvoiceResponse])
def get_invoices(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.Invoice)
    
    # Filter by user unless admin
    if current_user.role != models.UserRole.ADMIN:
        query = query.filter(models.Invoice.user_id == current_user.id)
    
    # Filter by status if provided
    if status:
        query = query.filter(models.Invoice.status == status)
    
    invoices = query.offset(skip).limit(limit).all()
    return invoices


# Get specific invoice
@router.get("/{invoice_id}", response_model=schemas.InvoiceDetailResponse)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Check authorization
    if invoice.user_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this invoice"
        )
    
    return invoice


# Update invoice status
@router.patch("/{invoice_id}", response_model=schemas.InvoiceResponse)
def update_invoice(
    invoice_id: int,
    invoice_update: schemas.InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Only admins can update invoices
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update invoices"
        )
    
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Update fields
    for key, value in invoice_update.dict(exclude_unset=True).items():
        setattr(invoice, key, value)
    
    db.commit()
    db.refresh(invoice)
    
    return invoice


# Cancel invoice
@router.post("/{invoice_id}/cancel", response_model=schemas.InvoiceResponse)
def cancel_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Only admins can cancel invoices
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel invoices"
        )
    
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Can only cancel if not paid
    if invoice.status == models.InvoiceStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel a paid invoice"
        )
    
    invoice.status = models.InvoiceStatus.CANCELLED
    
    db.commit()
    db.refresh(invoice)
    
    return invoice


# Download invoice PDF
@router.get("/{invoice_id}/pdf", response_class=Response)
def download_invoice_pdf(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Check authorization
    if invoice.user_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to download this invoice"
        )
    
    if not invoice.file_url:
        # Generate PDF if not already generated
        generate_invoice_pdf(invoice_id, db)
        db.refresh(invoice)
    
    if not invoice.file_url or not os.path.exists(invoice.file_url):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice PDF not found"
        )
    
    # Read the PDF file
    with open(invoice.file_url, "rb") as pdf_file:
        pdf_content = pdf_file.read()
    
    # Return the PDF file
    headers = {
        "Content-Disposition": f"attachment; filename=invoice_{invoice.invoice_number}.pdf",
        "Content-Type": "application/pdf"
    }
    
    return Response(content=pdf_content, headers=headers)


# Background task to generate invoice PDF
def generate_invoice_pdf(invoice_id: int, db: Session):
    """
    Generate PDF invoice using a template and store it
    """
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    
    if not invoice:
        return
    
    # Get line items
    line_items = db.query(models.InvoiceLineItem).filter(
        models.InvoiceLineItem.invoice_id == invoice_id
    ).all()
    
    # Get customer details
    customer = db.query(models.User).filter(models.User.id == invoice.user_id).first()
    
    # Get seller details if available
    seller = None
    if invoice.seller_id:
        seller = db.query(models.User).filter(models.User.id == invoice.seller_id).first()
    
    # Get order details if available
    order = None
    if invoice.order_id:
        order = db.query(models.Order).filter(models.Order.id == invoice.order_id).first()
        invoice.order = order  # Attach order to invoice for template rendering
    
    # Create the static directory if it doesn't exist
    static_dir = Path("static")
    static_dir.mkdir(exist_ok=True)
    
    # Create the invoices directory if it doesn't exist
    invoice_dir = Path("static/invoices")
    invoice_dir.mkdir(exist_ok=True)
    
    # Generate the PDF using our PDF generator
    pdf_path = pdf_generator.generate_invoice_pdf(
        invoice=invoice,
        line_items=line_items,
        customer=customer,
        seller=seller
    )
    
    # Define the destination path
    file_path = f"static/invoices/invoice_{invoice.invoice_number}.pdf"
    
    # Copy the generated PDF to the static directory
    shutil.copy(pdf_path, file_path)
    
    # Clean up the temporary file
    os.unlink(pdf_path)
    
    # Update invoice with file URL
    invoice.file_url = file_path
    db.commit()

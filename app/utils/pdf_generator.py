import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import io

from jinja2 import Environment, FileSystemLoader
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

from app.models import Invoice, InvoiceLineItem, User


class PDFGenerator:
    """Utility class for generating PDF documents using ReportLab."""
    
    def __init__(self):
        # Get the templates directory
        self.templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        self.env = Environment(loader=FileSystemLoader(self.templates_dir))
        # Initialize styles
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'Title',
            parent=self.styles['Heading1'],
            fontSize=16,
            alignment=1,  # Center alignment
            spaceAfter=12
        )
        self.heading_style = ParagraphStyle(
            'Heading',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=10
        )
        self.normal_style = self.styles['Normal']
        self.table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ])
    
    def generate_invoice_pdf(
        self, 
        invoice: Invoice, 
        line_items: List[InvoiceLineItem], 
        customer: User,
        seller: Optional[User] = None
    ) -> str:
        """
        Generate a PDF invoice from the invoice data using ReportLab.
        
        Args:
            invoice: The invoice object
            line_items: List of invoice line items
            customer: The customer user object
            seller: The seller user object (optional for B2C)
            
        Returns:
            str: Path to the generated PDF file
        """
        # Create a temporary file for the PDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            pdf_path = tmp.name
        
        # Create the PDF document
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Add invoice header
        elements.append(Paragraph(f"INVOICE #{invoice.invoice_number}", self.title_style))
        elements.append(Spacer(1, 0.25*inch))
        
        # Add invoice date and details
        elements.append(Paragraph(f"Date: {invoice.invoice_date.strftime('%d %b %Y')}", self.normal_style))
        elements.append(Paragraph(f"Due Date: {invoice.due_date.strftime('%d %b %Y') if invoice.due_date else 'N/A'}", self.normal_style))
        elements.append(Spacer(1, 0.25*inch))
        
        # Add customer and seller information
        elements.append(Paragraph("Customer Information:", self.heading_style))
        elements.append(Paragraph(f"Name: {customer.first_name} {customer.last_name}", self.normal_style))
        elements.append(Paragraph(f"Email: {customer.email}", self.normal_style))
        
        # Extract billing address
        billing_address = invoice.billing_address
        if billing_address:
            address_text = f"Address: {billing_address.address_line1}"
            if billing_address.address_line2:
                address_text += f", {billing_address.address_line2}"
            address_text += f", {billing_address.city}, {billing_address.state}, {billing_address.postal_code}"
            elements.append(Paragraph(address_text, self.normal_style))
        
        elements.append(Spacer(1, 0.25*inch))
        
        # Add seller information if available
        if seller:
            elements.append(Paragraph("Seller Information:", self.heading_style))
            elements.append(Paragraph(f"Name: {seller.first_name} {seller.last_name}", self.normal_style))
            elements.append(Paragraph(f"Email: {seller.email}", self.normal_style))
            elements.append(Spacer(1, 0.25*inch))
        
        # Add line items table
        elements.append(Paragraph("Invoice Items:", self.heading_style))
        
        # Create table data
        table_data = [["Item", "Description", "Quantity", "Unit Price", "Total"]]
        
        # Add line items to table
        for item in line_items:
            table_data.append([
                item.item_name,
                item.description or "",
                str(item.quantity),
                f"₹{item.unit_price:.2f}",
                f"₹{item.total_price:.2f}"
            ])
        
        # Add totals
        table_data.append(["", "", "", "Subtotal:", f"₹{invoice.subtotal:.2f}"])
        if invoice.tax_amount:
            table_data.append(["", "", "", "Tax:", f"₹{invoice.tax_amount:.2f}"])
        if invoice.discount_amount:
            table_data.append(["", "", "", "Discount:", f"₹{invoice.discount_amount:.2f}"])
        table_data.append(["", "", "", "Total:", f"₹{invoice.total_amount:.2f}"])
        
        # Create the table
        table = Table(table_data, colWidths=[1.5*inch, 2*inch, 1*inch, 1*inch, 1*inch])
        table.setStyle(self.table_style)
        elements.append(table)
        
        # Add payment information
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph("Payment Information:", self.heading_style))
        elements.append(Paragraph(f"Payment Status: {invoice.payment_status}", self.normal_style))
        elements.append(Paragraph(f"Payment Method: {invoice.payment_method or 'N/A'}", self.normal_style))
        
        # Add notes if available
        if invoice.notes:
            elements.append(Spacer(1, 0.25*inch))
            elements.append(Paragraph("Notes:", self.heading_style))
            elements.append(Paragraph(invoice.notes, self.normal_style))
        
        # Build the PDF
        doc.build(elements)
        
        return pdf_path
    
    def generate_receipt_pdf(self, payment_data: Dict[str, Any]) -> str:
        """
        Generate a PDF receipt for a payment.
        
        Args:
            payment_data: Dictionary containing payment details
            
        Returns:
            str: Path to the generated PDF file
        """
        # Create a temporary file for the PDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            pdf_path = tmp.name
        
        # Create the PDF document
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Add receipt header
        elements.append(Paragraph("PAYMENT RECEIPT", self.title_style))
        elements.append(Spacer(1, 0.25*inch))
        
        # Add receipt details
        elements.append(Paragraph(f"Receipt Number: {payment_data.get('payment_reference', 'N/A')}", self.normal_style))
        elements.append(Paragraph(f"Date: {datetime.now().strftime('%d %b %Y')}", self.normal_style))
        elements.append(Spacer(1, 0.25*inch))
        
        # Add payment details
        elements.append(Paragraph("Payment Details:", self.heading_style))
        elements.append(Paragraph(f"Amount: ₹{payment_data.get('amount', 0):.2f}", self.normal_style))
        elements.append(Paragraph(f"Payment Method: {payment_data.get('gateway', 'N/A')}", self.normal_style))
        elements.append(Paragraph(f"Transaction ID: {payment_data.get('gateway_payment_id', 'N/A')}", self.normal_style))
        elements.append(Paragraph(f"Status: {payment_data.get('status', 'N/A')}", self.normal_style))
        
        # Build the PDF
        doc.build(elements)
        
        return pdf_path


# Create a singleton instance
pdf_generator = PDFGenerator()

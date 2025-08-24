import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from app.models import Invoice, InvoiceLineItem, User


class PDFGenerator:
    """Utility class for generating PDF documents from templates."""
    
    def __init__(self):
        # Get the templates directory
        self.templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        self.env = Environment(loader=FileSystemLoader(self.templates_dir))
    
    def generate_invoice_pdf(
        self, 
        invoice: Invoice, 
        line_items: List[InvoiceLineItem], 
        customer: User,
        seller: Optional[User] = None
    ) -> str:
        """
        Generate a PDF invoice from the invoice data.
        
        Args:
            invoice: The invoice object
            line_items: List of invoice line items
            customer: The customer user object
            seller: The seller user object (optional for B2C)
            
        Returns:
            str: Path to the generated PDF file
        """
        # Get the template
        template = self.env.get_template("invoice_template.html")
        
        # Extract billing and shipping addresses
        billing_address = invoice.billing_address
        shipping_address = invoice.shipping_address if invoice.shipping_address else None
        
        # Render the template with the invoice data
        html_content = template.render(
            invoice=invoice,
            line_items=line_items,
            customer=customer,
            seller=seller,
            billing_address=billing_address,
            shipping_address=shipping_address,
            current_date=datetime.now().strftime("%d %b %Y")
        )
        
        # Create a temporary file for the PDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            # Generate the PDF
            HTML(string=html_content).write_pdf(tmp.name)
            pdf_path = tmp.name
        
        return pdf_path
    
    def generate_receipt_pdf(self, payment_data: Dict[str, Any]) -> str:
        """
        Generate a PDF receipt for a payment.
        
        Args:
            payment_data: Dictionary containing payment details
            
        Returns:
            str: Path to the generated PDF file
        """
        # This is a placeholder for future receipt generation
        # Implementation would be similar to invoice generation
        pass


# Create a singleton instance
pdf_generator = PDFGenerator()

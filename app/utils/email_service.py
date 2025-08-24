"""
Email service for sending notifications to users
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import BackgroundTasks
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

# Email configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "your-email@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "your-app-password")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "noreply@azlok.com")
SENDER_NAME = os.getenv("SENDER_NAME", "Azlok Enterprises")

# Setup Jinja2 template environment
template_dir = Path(__file__).parent.parent / "templates" / "emails"
template_dir.mkdir(parents=True, exist_ok=True)
env = Environment(loader=FileSystemLoader(str(template_dir)))


class EmailService:
    """Email service for sending notifications"""

    @staticmethod
    async def send_email_async(
        background_tasks: BackgroundTasks,
        recipient_email: str,
        subject: str,
        template_name: str,
        template_data: dict,
    ):
        """
        Schedule an email to be sent asynchronously
        """
        background_tasks.add_task(
            EmailService._send_email,
            recipient_email,
            subject,
            template_name,
            template_data,
        )

    @staticmethod
    def _send_email(
        recipient_email: str, subject: str, template_name: str, template_data: dict
    ):
        """
        Send an email using SMTP
        """
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
            message["To"] = recipient_email

            # Render template
            template = env.get_template(f"{template_name}.html")
            html_content = template.render(**template_data)

            # Attach parts
            message.attach(MIMEText(html_content, "html"))

            # Connect to SMTP server
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(message)

            return True
        except Exception as e:
            print(f"Failed to send email: {str(e)}")
            return False

    @staticmethod
    async def send_order_status_update(
        background_tasks: BackgroundTasks,
        order_id: str,
        order_number: str,
        customer_email: str,
        status: str,
        items: list,
        total: float,
    ):
        """
        Send order status update notification
        """
        subject = f"Order #{order_number} Status Update: {status.title()}"
        template_name = "order_status_update"
        template_data = {
            "order_id": order_id,
            "order_number": order_number,
            "status": status,
            "items": items,
            "total": total,
            "status_description": get_status_description(status),
        }

        await EmailService.send_email_async(
            background_tasks, customer_email, subject, template_name, template_data
        )

    @staticmethod
    async def send_seller_order_notification(
        background_tasks: BackgroundTasks,
        seller_email: str,
        order_number: str,
        customer_name: str,
        items: list,
        total: float,
    ):
        """
        Send notification to seller about new order
        """
        subject = f"New Order #{order_number} Received"
        template_name = "seller_order_notification"
        template_data = {
            "order_number": order_number,
            "customer_name": customer_name,
            "items": items,
            "total": total,
        }

        await EmailService.send_email_async(
            background_tasks, seller_email, subject, template_name, template_data
        )


def get_status_description(status: str) -> str:
    """
    Get description for order status
    """
    descriptions = {
        "pending": "Your order has been received and is being processed.",
        "processing": "Your order is being prepared for shipping.",
        "shipped": "Your order has been shipped and is on its way to you.",
        "delivered": "Your order has been delivered.",
        "cancelled": "Your order has been cancelled.",
    }
    return descriptions.get(status, "Your order status has been updated.")

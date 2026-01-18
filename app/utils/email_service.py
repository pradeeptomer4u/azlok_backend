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
import logging

logger = logging.getLogger(__name__)

# Email configuration - GoDaddy SMTP
SMTP_SERVER = "smtpout.secureserver.net"
SMTP_PORT = "465"
SMTP_USERNAME = "hello@azlok.com"
SMTP_PASSWORD = "Indiaa@1424"
SENDER_EMAIL ="hello@azlok.com"
SENDER_NAME = "Azlok Pvt Ltd"

# Setup Jinja2 template environment
template_dir = Path(__file__).parent.parent / "templates" / "emails"
template_dir.mkdir(parents=True, exist_ok=True)
env = Environment(loader=FileSystemLoader(str(template_dir)))


class EmailService:
    """Email service for sending notifications"""

    @staticmethod
    def send_email(
        recipient_email: str,
        subject: str,
        template_name: str,
        template_data: dict,
    ):
        """
        Send an email synchronously (for testing or direct sending)
        """
        return EmailService._send_email(
            recipient_email,
            subject,
            template_name,
            template_data,
        )

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
            print(f"[EMAIL SERVICE] Starting email send to {recipient_email}")
            logger.info(f"Preparing to send email to {recipient_email}")
            logger.info(f"Subject: {subject}")
            
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
            message["To"] = recipient_email
            print(f"[EMAIL SERVICE] Message created - From: {SENDER_EMAIL}, To: {recipient_email}")

            # Render template
            try:
                template = env.get_template(f"{template_name}.html")
                html_content = template.render(**template_data)
                logger.info(f"Template {template_name}.html rendered successfully")
                print(f"[EMAIL SERVICE] Template {template_name}.html rendered successfully")
            except Exception as template_error:
                print(f"[EMAIL SERVICE ERROR] Template rendering failed: {str(template_error)}")
                raise

            # Attach parts
            message.attach(MIMEText(html_content, "html"))

            # Connect to SMTP server (using SSL for port 465)
            print(f"[EMAIL SERVICE] Connecting to {SMTP_SERVER}:{SMTP_PORT}")
            logger.info(f"Connecting to {SMTP_SERVER}:{SMTP_PORT}")
            
            with smtplib.SMTP_SSL(SMTP_SERVER, int(SMTP_PORT)) as server:
                logger.info("Connected to SMTP server")
                print(f"[EMAIL SERVICE] Connected to SMTP server")
                
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                logger.info("Authentication successful")
                print(f"[EMAIL SERVICE] Authentication successful")
                
                result = server.send_message(message)
                logger.info(f"Email sent successfully. Server response: {result}")
                print(f"[EMAIL SERVICE] Email sent successfully. Server response: {result}")

            logger.info(f"Email to {recipient_email} sent successfully")
            print(f"[EMAIL SERVICE] ✅ Email to {recipient_email} sent successfully")
            return True
        except Exception as e:
            error_msg = f"Failed to send email to {recipient_email}: {str(e)}"
            logger.error(error_msg)
            logger.exception("Email sending error details:")
            print(f"[EMAIL SERVICE ERROR] {error_msg}")
            import traceback
            print(f"[EMAIL SERVICE ERROR] Full traceback: {traceback.format_exc()}")
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

    @staticmethod
    def send_password_reset_email_sync(
        recipient_email: str,
        reset_token: str,
        user_name: str,
    ):
        """
        Send password reset email synchronously (without background tasks)
        """
        subject = "Password Reset Request - Azlok"
        template_name = "password_reset"
        reset_url = f"https://azlok.com/reset-password?token={reset_token}"
        template_data = {
            "user_name": user_name,
            "reset_url": reset_url,
            "reset_token": reset_token,
        }

        return EmailService.send_email(
            recipient_email, subject, template_name, template_data
        )

    @staticmethod
    async def send_password_reset_email(
        background_tasks: BackgroundTasks,
        recipient_email: str,
        reset_token: str,
        user_name: str,
    ):
        """
        Send password reset email with reset token (async with background tasks)
        """
        subject = "Password Reset Request - Azlok"
        template_name = "password_reset"
        reset_url = f"https://azlok.com/reset-password?token={reset_token}"
        template_data = {
            "user_name": user_name,
            "reset_url": reset_url,
            "reset_token": reset_token,
        }

        await EmailService.send_email_async(
            background_tasks, recipient_email, subject, template_name, template_data
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

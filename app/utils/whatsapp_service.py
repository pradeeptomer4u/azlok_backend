"""
WhatsApp service for sending simple notifications
Can be integrated with any WhatsApp gateway service
"""
import logging
import os
from typing import Optional
import requests

logger = logging.getLogger(__name__)

# WhatsApp API Configuration - Green API
# Green API credentials
GREEN_API_URL = "https://7105.api.greenapi.com"
GREEN_API_INSTANCE_ID = "7105476617"
GREEN_API_TOKEN = "8fab8360a9e64b1f8dcd6963ccedbfc997551c96bc0a43f2af"
WHATSAPP_ENABLED = True

# Construct the full API endpoint for sending messages
WHATSAPP_API_URL = f"{GREEN_API_URL}/waInstance{GREEN_API_INSTANCE_ID}/sendMessage/{GREEN_API_TOKEN}"

class WhatsAppService:
    """Simple WhatsApp notification service"""
    
    @staticmethod
    def send_order_notification(
        phone_number: str,
        order_number: str,
        customer_name: str,
        customer_phone: str,
        total_amount: float,
        items_count: int,
        shipping_address: dict,
        product_names: list
    ) -> bool:
        """
        Send WhatsApp notification for new order
        
        Args:
            phone_number: Recipient phone number (with country code, e.g., +919876543210)
            order_number: Order number
            customer_name: Customer name
            customer_phone: Customer phone number
            total_amount: Total order amount
            items_count: Number of items in order
            shipping_address: Shipping address dictionary
            product_names: List of product names
        
        Returns:
            bool: True if message sent successfully, False otherwise
        """
        try:
            # Format product list
            products_text = "\n".join([f"  • {name}" for name in product_names[:5]])  # Limit to 5 products
            if len(product_names) > 5:
                products_text += f"\n  • ...and {len(product_names) - 5} more"
            
            # Format address
            address_text = f"{shipping_address.get('address_line1', '')}"
            if shipping_address.get('address_line2'):
                address_text += f", {shipping_address.get('address_line2')}"
            address_text += f"\n{shipping_address.get('city', '')}, {shipping_address.get('state', '')} {shipping_address.get('zip_code', '')}"
            
            # Format the message
            message = f"""
🎉 *New Order Alert!*

📦 *Order:* #{order_number}

👤 *Customer Details:*
Name: {customer_name}
Phone: {customer_phone}

📍 *Shipping Address:*
{address_text}

🛍️ *Products:*
{products_text}

💰 *Total Amount:* ₹{total_amount:.2f}
📋 *Total Items:* {items_count}

Please check your admin panel for complete details.
            """.strip()
            
            logger.info(f"WhatsApp notification prepared for {phone_number}")
            logger.info(f"Message: {message}")
            
            # Check if WhatsApp is enabled
            if not WHATSAPP_ENABLED:
                # Just log the message
                print(f"\n{'='*50}")
                print(f"WhatsApp Message to {phone_number}:")
                print(f"{'='*50}")
                print(message)
                print(f"{'='*50}\n")
                logger.info("WhatsApp API disabled. Message logged only.")
                return True
            
            # Send via Green API
            try:
                # Green API payload structure
                # Phone number format: without + sign, with country code (e.g., 917300551699)
                clean_phone = phone_number.replace("+", "").replace("-", "").replace(" ", "")
                
                payload = {
                    "chatId": f"{clean_phone}@c.us",  # Green API format
                    "message": message
                }
                
                headers = {
                    "Content-Type": "application/json"
                }
                
                logger.info(f"Sending WhatsApp message via Green API to {phone_number}")
                response = requests.post(
                    WHATSAPP_API_URL,
                    json=payload,
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code in [200, 201]:
                    logger.info(f"WhatsApp message sent successfully: {response.json()}")
                    print(f"✅ WhatsApp sent to {phone_number}")
                    return True
                else:
                    logger.error(f"Green API error: {response.status_code} - {response.text}")
                    print(f"❌ WhatsApp failed: {response.text}")
                    return False
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Green API request failed: {str(e)}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp notification: {str(e)}")
            return False
    
    @staticmethod
    def send_simple_message(phone_number: str, message: str) -> bool:
        """
        Send a simple WhatsApp message
        
        Args:
            phone_number: Recipient phone number (with country code)
            message: Message text to send
        
        Returns:
            bool: True if message sent successfully, False otherwise
        """
        try:
            logger.info(f"Sending WhatsApp message to {phone_number}")
            
            # Check if WhatsApp is enabled
            if not WHATSAPP_ENABLED:
                # Just log the message
                print(f"\n{'='*50}")
                print(f"WhatsApp Message to {phone_number}:")
                print(f"{'='*50}")
                print(message)
                print(f"{'='*50}\n")
                logger.info("WhatsApp API disabled. Message logged only.")
                return True
            
            # Send via Green API
            try:
                clean_phone = phone_number.replace("+", "").replace("-", "").replace(" ", "")
                
                payload = {
                    "chatId": f"{clean_phone}@c.us",
                    "message": message
                }
                
                headers = {
                    "Content-Type": "application/json"
                }
                
                response = requests.post(
                    WHATSAPP_API_URL,
                    json=payload,
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code in [200, 201]:
                    logger.info(f"WhatsApp message sent successfully")
                    print(f"✅ WhatsApp sent to {phone_number}")
                    return True
                else:
                    logger.error(f"Green API error: {response.status_code} - {response.text}")
                    print(f"❌ WhatsApp failed: {response.text}")
                    return False
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Green API request failed: {str(e)}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {str(e)}")
            return False

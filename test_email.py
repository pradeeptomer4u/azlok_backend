"""
Test script to send a password reset email
"""
import sys
import os
import logging
sys.path.insert(0, os.path.dirname(__file__))

# Configure logging to see detailed output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from app.utils.email_service import EmailService, SMTP_SERVER, SMTP_PORT

def test_password_reset_email():
    """Test sending a password reset email"""
    
    # Test email details
    recipient_email = "pradeeptomer4u@gmail.com"
    reset_token = "test-token-123456789"
    user_name = "Test User"
    
    print(f"Attempting to send password reset email to: {recipient_email}")
    print(f"Using SMTP server: {SMTP_SERVER}:{SMTP_PORT}")
    print(f"From: hello@azlok.com")
    print("-" * 50)
    
    try:
        # Prepare email data
        subject = "Password Reset Request - Azlok"
        template_name = "password_reset"
        reset_url = f"https://azlok.com/reset-password?token={reset_token}"
        template_data = {
            "user_name": user_name,
            "reset_url": reset_url,
            "reset_token": reset_token,
        }
        
        # Send the email synchronously
        result = EmailService.send_email(
            recipient_email=recipient_email,
            subject=subject,
            template_name=template_name,
            template_data=template_data
        )
        
        if result:
            print("✓ Email sent successfully!")
            print(f"Check inbox at: {recipient_email}")
        else:
            print("✗ Email sending failed. Check logs for details.")
        
    except Exception as e:
        print(f"✗ Error sending email: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_password_reset_email()

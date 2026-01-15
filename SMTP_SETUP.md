# SMTP Email Setup Guide

## Issue
Forgot password emails are not sending because SMTP environment variables are not configured.

## Solution

### Step 1: Set up Gmail App Password (if using Gmail)

1. Go to your Google Account settings
2. Enable 2-Factor Authentication if not already enabled
3. Go to Security → 2-Step Verification → App passwords
4. Generate a new app password for "Mail"
5. Copy the 16-character password

### Step 2: Create `.env` file

Create a `.env` file in the project root (`/Users/pradeep/dd/azlok_backend/.env`) with the following:

```bash
# SMTP Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-actual-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
SENDER_EMAIL=your-actual-email@gmail.com
SENDER_NAME=Azlok Enterprises
```

**Important Notes:**
- Replace `your-actual-email@gmail.com` with your Gmail address
- Replace `your-16-char-app-password` with the app password from Step 1
- For Gmail, `SENDER_EMAIL` should match `SMTP_USERNAME`
- Do NOT use your regular Gmail password, use the app password

### Step 3: Alternative SMTP Providers

#### Using SendGrid
```bash
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-sendgrid-api-key
SENDER_EMAIL=noreply@azlok.com
SENDER_NAME=Azlok Enterprises
```

#### Using Mailgun
```bash
SMTP_SERVER=smtp.mailgun.org
SMTP_PORT=587
SMTP_USERNAME=postmaster@your-domain.mailgun.org
SMTP_PASSWORD=your-mailgun-smtp-password
SENDER_EMAIL=noreply@azlok.com
SENDER_NAME=Azlok Enterprises
```

### Step 4: Load Environment Variables

If running locally with uvicorn, install python-dotenv:
```bash
pip install python-dotenv
```

Then add to the top of `main.py`:
```python
from dotenv import load_dotenv
load_dotenv()
```

### Step 5: Test the Setup

1. Restart your application
2. Try the forgot password endpoint
3. Check the logs for any SMTP errors

### Troubleshooting

**Error: "Authentication failed"**
- Verify you're using an app password, not your regular password
- Check that 2FA is enabled on your Google account

**Error: "Connection refused"**
- Check your firewall settings
- Verify SMTP_PORT is 587 (or 465 for SSL)

**Error: "Sender address rejected"**
- Make sure SENDER_EMAIL matches SMTP_USERNAME for Gmail
- Verify the email address is verified with your SMTP provider

**Emails still not sending**
- Check application logs for detailed error messages
- Verify all environment variables are loaded correctly
- Test SMTP credentials with a simple Python script

### Verification Script

Create `test_email.py` to test SMTP configuration:
```python
import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

try:
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        
        msg = MIMEText("Test email from Azlok")
        msg["Subject"] = "Test Email"
        msg["From"] = SENDER_EMAIL
        msg["To"] = "test@example.com"
        
        server.send_message(msg)
        print("✓ Email sent successfully!")
except Exception as e:
    print(f"✗ Error: {e}")
```

Run: `python test_email.py`

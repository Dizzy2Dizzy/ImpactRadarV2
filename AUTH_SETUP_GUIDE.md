# Authentication Setup Guide

Your Impact Radar platform now has a complete authentication system with both email and phone verification. Follow these steps to configure it:

## Authentication Features

✅ **Login/Signup Pages**: Users can create accounts with email OR phone number
✅ **Verification Codes**: 6-digit codes sent via email or SMS (10-minute expiry)
✅ **Password Security**: SHA-256 hashed passwords stored in database
✅ **Session Management**: Streamlit session state tracks logged-in users
✅ **Protected Pages**: All app pages require authentication
✅ **Logout**: Users can logout from header

## Required Setup: Email Verification (SMTP)

To enable **email verification**, you need to configure SMTP credentials. Here are your options:

### Option 1: Gmail SMTP (Recommended for Testing - Free)

1. **Create an App Password** (required for Gmail):
   - Go to your Google Account: https://myaccount.google.com/security
   - Enable 2-Factor Authentication if not already enabled
   - Go to "App passwords": https://myaccount.google.com/apppasswords
   - Create a new app password for "Mail"
   - Copy the 16-character password (e.g., `abcd efgh ijkl mnop`)

2. **Add these secrets to your Replit project**:
   ```
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your.email@gmail.com
   SMTP_PASSWORD=your-16-char-app-password
   FROM_EMAIL=your.email@gmail.com
   ```

### Option 2: SendGrid (100 Free Emails/Day)

1. **Create SendGrid Account**: https://signup.sendgrid.com/
2. **Create API Key**: 
   - Go to Settings > API Keys
   - Create API Key with "Mail Send" permissions
   - Copy the API key

3. **Add these secrets**:
   ```
   SMTP_HOST=smtp.sendgrid.net
   SMTP_PORT=587
   SMTP_USER=apikey
   SMTP_PASSWORD=your-sendgrid-api-key
   FROM_EMAIL=your-verified-sender@example.com
   ```

### Option 3: Other SMTP Providers

You can use any SMTP provider (Mailgun, AWS SES, etc.). Just set these variables:
- `SMTP_HOST`: Your SMTP server hostname
- `SMTP_PORT`: Usually 587 or 465
- `SMTP_USER`: Your SMTP username
- `SMTP_PASSWORD`: Your SMTP password
- `FROM_EMAIL`: The email address to send from

## Optional Setup: Phone Verification (Twilio)

To enable **SMS/phone verification**, you need a Twilio account:

1. **Create Twilio Account**: https://www.twilio.com/try-twilio
   - Get $15 free credit for testing

2. **Get your credentials**:
   - Account SID: Found on Twilio Console Dashboard
   - Auth Token: Found on Twilio Console Dashboard
   - Phone Number: Get a free trial number from Twilio

3. **Install Twilio library**:
   ```bash
   pip install twilio
   ```

4. **Add these secrets to Replit**:
   ```
   TWILIO_ACCOUNT_SID=your-account-sid
   TWILIO_AUTH_TOKEN=your-auth-token
   TWILIO_PHONE_NUMBER=+1234567890
   ```

## ⚠️ IMPORTANT: How to Securely Add Credentials

**NEVER hardcode API keys or passwords in your code!**

Use Replit's built-in Secrets Manager to securely store credentials:

1. Click on "Tools" in the left sidebar
2. Click on "Secrets" (🔒 icon)
3. Add each environment variable with its value:
   - Click "+ New Secret"
   - Enter the key name (e.g., `SMTP_HOST`)
   - Enter the value
   - Click "Add Secret"
4. Repeat for all required credentials
5. Restart your application for changes to take effect

**Why use Secrets?**
- ✅ Credentials are encrypted and secure
- ✅ Not visible in code or version control
- ✅ Automatically available as environment variables
- ✅ Different values for development vs production
- ❌ **NEVER** commit credentials to Git
- ❌ **NEVER** paste credentials directly in code files

## Testing the Authentication System

### Without Email/SMS Setup (Demo Mode):

The system will show helpful error messages:
- "Email service not configured. Please set SMTP credentials."
- "SMS service not configured. Please set Twilio credentials."

### With Email Setup:

1. Click "Create Account"
2. Choose "Email" signup method
3. Enter your email and password
4. You'll receive a 6-digit verification code by email
5. Enter the code to verify your account
6. Login with your email and password

### With Phone Setup:

1. Click "Create Account"
2. Choose "Phone" signup method
3. Enter phone number (format: +1234567890)
4. You'll receive a 6-digit verification code by SMS
5. Enter the code to verify your account
6. Login with your phone and password

## Security Features

- **Password Hashing**: Passwords are hashed using SHA-256 before storage
- **Code Expiry**: Verification codes expire after 10 minutes
- **One-time Codes**: Verification codes can only be used once
- **Session Security**: User sessions are managed securely via Streamlit
- **Protected Routes**: All pages require authentication

## Database Tables

The system uses two new PostgreSQL tables:

### `users` table:
- `id`: User ID (auto-increment)
- `email`: User email (unique, optional)
- `phone`: User phone (unique, optional)
- `password_hash`: Hashed password
- `is_verified`: Verification status
- `verification_method`: 'email' or 'phone'
- `created_at`: Account creation timestamp
- `last_login`: Last login timestamp

### `verification_codes` table:
- `id`: Code ID (auto-increment)
- `user_id`: Associated user ID
- `code`: 6-digit verification code
- `method`: 'email' or 'phone'
- `expires_at`: Expiration timestamp
- `used`: Whether code has been used
- `created_at`: Code creation timestamp

## Next Steps

1. **Configure Email or Phone verification** (or both) using the instructions above
2. **Test the signup flow** by creating a new account
3. **Verify the account** using the code sent to your email/phone
4. **Login** to access the Impact Radar platform

## Future Enhancements (Optional)

You can extend the authentication system with:
- Password reset functionality
- Email change verification
- Two-factor authentication (2FA)
- OAuth login (Google, Facebook, etc.)
- User profile management
- Account deletion

---

**Need help?** Check the error messages in the app - they'll guide you through missing configuration steps.

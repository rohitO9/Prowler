# Email Configuration Guide

This guide explains how to configure email settings for sending invitation emails.

## Required Environment Variables

Add the following environment variables to your `.env` file in the `api/src/backend/` directory:

### Basic Email Configuration

```env
# Email Backend
# Options:
# - django.core.mail.backends.console.EmailBackend (for development - prints to console)
# - django.core.mail.backends.smtp.EmailBackend (for production - sends real emails)
DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend

# SMTP Server Configuration
DJANGO_EMAIL_HOST=smtp.gmail.com
DJANGO_EMAIL_PORT=587
DJANGO_EMAIL_USE_TLS=True
DJANGO_EMAIL_USE_SSL=False

# SMTP Authentication
DJANGO_EMAIL_HOST_USER=your-email@gmail.com
DJANGO_EMAIL_HOST_PASSWORD=your-app-password

# Default From Email (shown as sender)
DJANGO_DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Frontend URL (used in invitation links)
FRONTEND_URL=http://localhost:3000
```

## Email Provider Examples

### Gmail Configuration

```env
DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DJANGO_EMAIL_HOST=smtp.gmail.com
DJANGO_EMAIL_PORT=587
DJANGO_EMAIL_USE_TLS=True
DJANGO_EMAIL_USE_SSL=False
DJANGO_EMAIL_HOST_USER=your-email@gmail.com
DJANGO_EMAIL_HOST_PASSWORD=your-app-password  # Use App Password, not regular password
DJANGO_DEFAULT_FROM_EMAIL=noreply@yourdomain.com
FRONTEND_URL=http://localhost:3000
```

**Important for Gmail:**
- Enable 2-Factor Authentication
- Generate an **App Password** (not your regular password)
- Use the App Password in `DJANGO_EMAIL_HOST_PASSWORD`

### Outlook/Office 365 Configuration

```env
DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DJANGO_EMAIL_HOST=smtp.office365.com
DJANGO_EMAIL_PORT=587
DJANGO_EMAIL_USE_TLS=True
DJANGO_EMAIL_USE_SSL=False
DJANGO_EMAIL_HOST_USER=your-email@outlook.com
DJANGO_EMAIL_HOST_PASSWORD=your-password
DJANGO_DEFAULT_FROM_EMAIL=noreply@yourdomain.com
FRONTEND_URL=http://localhost:3000
```

### SendGrid Configuration

```env
DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DJANGO_EMAIL_HOST=smtp.sendgrid.net
DJANGO_EMAIL_PORT=587
DJANGO_EMAIL_USE_TLS=True
DJANGO_EMAIL_USE_SSL=False
DJANGO_EMAIL_HOST_USER=apikey
DJANGO_EMAIL_HOST_PASSWORD=your-sendgrid-api-key
DJANGO_DEFAULT_FROM_EMAIL=noreply@yourdomain.com
FRONTEND_URL=http://localhost:3000
```

### Amazon SES Configuration

```env
DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DJANGO_EMAIL_HOST=email-smtp.us-east-1.amazonaws.com  # Replace with your region
DJANGO_EMAIL_PORT=587
DJANGO_EMAIL_USE_TLS=True
DJANGO_EMAIL_USE_SSL=False
DJANGO_EMAIL_HOST_USER=your-ses-access-key-id
DJANGO_EMAIL_HOST_PASSWORD=your-ses-secret-access-key
DJANGO_DEFAULT_FROM_EMAIL=noreply@yourdomain.com
FRONTEND_URL=http://localhost:3000
```

## Development Configuration (Console Backend)

For development/testing, you can use the console backend which prints emails to the console instead of sending them:

```env
DJANGO_EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DJANGO_DEFAULT_FROM_EMAIL=no-reply@localhost
FRONTEND_URL=http://localhost:3000
```

When using the console backend, you don't need to configure SMTP settings.

## Testing Email Configuration

After configuring your email settings:

1. Restart your Django server
2. Send a test invitation from the Azure AD config page
3. Check:
   - **Console Backend**: Check your Django console for email output
   - **SMTP Backend**: Check the recipient's inbox (and spam folder)

## Security Best Practices

1. **Never commit `.env` file to version control**
2. **Use App Passwords** for Gmail instead of regular passwords
3. **Use environment variables** for sensitive credentials
4. **Use a dedicated email service** (SendGrid, SES) for production
5. **Verify your domain** for better email deliverability

## Troubleshooting

### Emails not sending?

1. Check if `DJANGO_EMAIL_BACKEND` is set to SMTP backend
2. Verify SMTP credentials are correct
3. Check firewall/network settings (some networks block SMTP)
4. For Gmail: Ensure 2FA is enabled and App Password is used
5. Check Django logs for error messages

### "Connection refused" errors?

- Verify `DJANGO_EMAIL_HOST` and `DJANGO_EMAIL_PORT` are correct
- Check if your network allows SMTP connections
- Try using port 465 with SSL instead of 587 with TLS

### Emails going to spam?

- Use a dedicated email service (SendGrid, SES, Mailgun)
- Verify your domain with SPF, DKIM, and DMARC records
- Use a professional `DJANGO_DEFAULT_FROM_EMAIL` address


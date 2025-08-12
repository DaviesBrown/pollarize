# PythonAnywhere Deployment Guide

This guide explains how to deploy the Pollarize API on PythonAnywhere's free plan.

## Prerequisites

1. PythonAnywhere free account
2. Paystack account for payment processing
3. Basic knowledge of Django deployment

## Limitations on Free Plan

- **No Redis/Celery**: Background tasks run synchronously
- **No MySQL**: SQLite database only
- **Limited CPU seconds**: 100 seconds/day
- **No external internet access**: Some geolocation services may not work
- **No HTTPS**: Only HTTP available

## Step-by-Step Deployment

### 1. Upload Your Code

```bash
# In PythonAnywhere console
cd ~
git clone https://github.com/yourusername/pollarize.git
cd pollarize
```

### 2. Install Dependencies

```bash
pip3.10 install --user -r requirements-pythonanywhere.txt
```

### 3. Environment Configuration

Create `.env` file in your project root:

```bash
cp .env.example .env
```

Edit `.env` with your settings:
```bash
DJANGO_SECRET_KEY=your-very-secure-secret-key-here
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=yourusername.pythonanywhere.com
PAYSTACK_PUBLIC_KEY=pk_test_your_paystack_public_key
PAYSTACK_SECRET_KEY=sk_test_your_paystack_secret_key
CELERY_ALWAYS_EAGER=1
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
STATIC_ROOT=/home/yourusername/pollarize/static
```

### 4. Database Setup

```bash
python3.10 manage.py collectstatic --noinput
python3.10 manage.py migrate
python3.10 manage.py createsuperuser
```

### 5. Web App Configuration

In PythonAnywhere Dashboard:

1. Go to **Web** tab
2. Click **Add a new web app**
3. Choose **Manual configuration (advanced)**
4. Choose **Python 3.10**

Configure the following:

**Source code:** `/home/yourusername/pollarize`

**WSGI configuration file:** Edit `/var/www/yourusername_pythonanywhere_com_wsgi.py`:

```python
import os
import sys

# Add your project directory to sys.path
path = '/home/yourusername/pollarize'
if path not in sys.path:
    sys.path.insert(0, path)

# Set environment variable for Django settings
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

**Static files:**
- URL: `/static/`
- Directory: `/home/yourusername/pollarize/static`

### 6. Environment Variables

In the **Files** tab, create `/home/yourusername/.env` or add to your WSGI file:

```python
# Add to WSGI file before Django setup
os.environ.setdefault('DJANGO_SECRET_KEY', 'your-secret-key')
os.environ.setdefault('DJANGO_DEBUG', '0')
os.environ.setdefault('DJANGO_ALLOWED_HOSTS', 'yourusername.pythonanywhere.com')
# ... other environment variables
```

### 7. Test Your Deployment

1. Click **Reload** on the Web tab
2. Visit `http://yourusername.pythonanywhere.com`
3. Test API endpoints: `http://yourusername.pythonanywhere.com/api/v1/`
4. Check Swagger docs: `http://yourusername.pythonanywhere.com/swagger/`

## API Endpoints Available

All endpoints are available under `/api/v1/`:

- **Authentication**: `/api/v1/auth/`
- **Polls**: `/api/v1/polls/`
- **Payments**: `/api/v1/payments/`
- **Analytics**: `/api/v1/analytics/`
- **Compliance**: `/api/v1/compliance/`

## Important Notes

### Free Plan Considerations

1. **Database**: Uses SQLite - suitable for development/testing
2. **Background Tasks**: Run synchronously (no Celery)
3. **File Storage**: Limited to account storage quota
4. **External APIs**: Geolocation services may have limited access

### Production Recommendations

For production use, consider upgrading to a paid plan for:
- MySQL database
- HTTPS support
- More CPU seconds
- Better performance
- Redis/Celery support

## Troubleshooting

### Common Issues

1. **ImportError**: Check Python path in WSGI file
2. **Static files not loading**: Verify static files configuration
3. **Database errors**: Run migrations again
4. **Environment variables**: Check `.env` file or WSGI configuration

### Logs

Check error logs in PythonAnywhere Dashboard under **Tasks** > **Error log**.

## Security Checklist

- [ ] Change `DJANGO_SECRET_KEY` from default
- [ ] Set `DJANGO_DEBUG=0` in production
- [ ] Configure proper `ALLOWED_HOSTS`
- [ ] Use environment variables for sensitive data
- [ ] Set up proper Paystack webhook endpoints

## Getting API Keys

### Paystack Keys

1. Sign up at [Paystack](https://paystack.com/)
2. Go to Settings > API Keys & Webhooks
3. Copy your test/live public and secret keys
4. Add webhook URL: `http://yourusername.pythonanywhere.com/api/v1/webhook/paystack/`

### Database (Paid Plans)

For MySQL on paid plans:
1. Go to **Databases** tab in PythonAnywhere
2. Create a MySQL database
3. Note the connection details
4. Update your `.env` file with MySQL settings

That's it! Your Pollarize API should now be running on PythonAnywhere.

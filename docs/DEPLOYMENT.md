# PythonAnywhere Deployment Guide for Pollarize API

## Prerequisites
1. PythonAnywhere free account
2. MySQL database (included in free tier)
3. Python 3.10+ environment

## Setup Instructions

### 1. Database Setup
```bash
# In PythonAnywhere MySQL console
CREATE DATABASE pollarize_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. Environment Variables
Create a `.env` file in your project root:
```bash
# Database
DB_ENGINE=django.db.backends.mysql
DB_NAME=yourusername$pollarize_db
DB_USER=yourusername
DB_PASSWORD=your_mysql_password
DB_HOST=yourusername.mysql.pythonanywhere-services.com
DB_PORT=3306

# Django
DJANGO_SECRET_KEY=your-super-secret-key-here
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOST=yourusername.pythonanywhere.com

# Disable Redis on free tier
USE_REDIS=0

# Disable background tasks on free tier
CELERY_ALWAYS_EAGER=1

# Analytics settings
ANALYTICS_RETENTION_DAYS=90
COMPLIANCE_LOG_RETENTION_DAYS=90

# Payment settings (optional)
PAYSTACK_PUBLIC_KEY=your_paystack_public_key
PAYSTACK_SECRET_KEY=your_paystack_secret_key

# Disable geo restrictions for testing
ENABLE_GEO_RESTRICTIONS=0
```

### 3. Installation Commands
```bash
# In PythonAnywhere Bash console
cd /home/yourusername
git clone https://github.com/yourusername/pollarize.git
cd pollarize

# Install dependencies
pip install --user -r requirements.txt

# Create cache table (since we're not using Redis)
python manage.py createcachetable

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

### 4. WSGI Configuration
Update your WSGI file at `/var/www/yourusername_pythonanywhere_com_wsgi.py`:

```python
import os
import sys

# Add your project directory to sys.path
path = '/home/yourusername/pollarize'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### 5. Static Files Configuration
In the PythonAnywhere Web tab:
- Static URL: `/static/`
- Static Directory: `/home/yourusername/pollarize/staticfiles/`

### 6. Testing API Endpoints
```bash
# Test basic functionality
curl https://yourusername.pythonanywhere.com/api/v1/polls/

# Test analytics dashboard (requires authentication)
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     https://yourusername.pythonanywhere.com/api/v1/analytics/dashboard/

# Test compliance logs (admin only)
curl -H "Authorization: Bearer YOUR_ADMIN_JWT_TOKEN" \
     https://yourusername.pythonanywhere.com/api/v1/compliance/logs/
```

### 7. Maintenance Commands
```bash
# Update analytics manually (since no background workers)
python manage.py update_analytics --all-polls

# Clean up old data
python manage.py cleanup_compliance --days 90

# Create analytics snapshots
python manage.py update_analytics --create-snapshot daily
```

## Limitations on Free Tier
1. No background workers (Celery disabled)
2. No Redis (using database cache)
3. Limited CPU time
4. Single MySQL database
5. 512MB storage limit

## Performance Optimizations for Free Tier
1. Use database-level caching
2. Implement pagination on all list endpoints
3. Limit analytics retention periods
4. Use database indexes effectively
5. Compress static files

## Upgrading to Paid Plans
- **Hacker Plan ($5/month)**: More CPU time, always-on tasks
- **Web Developer Plan ($12/month)**: Multiple domains, more storage
- **Postgres databases available on paid plans**

## Troubleshooting
1. Check error logs in PythonAnywhere dashboard
2. Verify environment variables in `.env` file
3. Ensure MySQL credentials are correct
4. Check static files are collected properly
5. Verify ALLOWED_HOSTS includes your domain

## API Documentation
Access Swagger documentation at:
`https://yourusername.pythonanywhere.com/swagger/`

## Security Notes
1. Change default secret key
2. Set DEBUG=False in production
3. Use HTTPS (automatic on PythonAnywhere)
4. Regularly update dependencies
5. Monitor compliance logs for suspicious activity

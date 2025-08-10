# Phase 5: Notifications & Production Readiness

## Architecture Overview

Phase 5 implements a multi-channel notification system and prepares the application for production deployment with security hardening, monitoring, and deployment configuration. We'll create notification preferences, dispatch mechanisms, and production-grade infrastructure setup.

## Technical Design Decisions

1. **Notification Architecture**:
   - Channel-agnostic model with delivery strategies
   - User preference system with fine-grained control
   - Retry mechanism with exponential backoff
   - Template-based content generation

2. **Production Hardening**:
   - Security header configuration
   - HTTPS enforcement and CORS protection
   - Rate limiting and throttling
   - Comprehensive logging and monitoring

3. **Deployment Strategy**:
   - PythonAnywhere-optimized configuration
   - Static/media file handling
   - Background task workarounds for free tier
   - Health check and monitoring endpoints

## Implementation Tasks

### 1. Notification Models (2 days)

```python
# apps/notifications/models.py
class NotificationPreference(models.Model):
    """User preferences for different notification types"""
    CHANNEL_CHOICES = (
        ('email', 'Email'),
        ('in_app', 'In-App'),
    )
    
    user = models.ForeignKey('core.User', on_delete=models.CASCADE, related_name='notification_preferences')
    notification_type = models.CharField(max_length=50)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    enabled = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('user', 'notification_type', 'channel')
        indexes = [
            models.Index(fields=['user', 'notification_type']),
        ]

class Notification(models.Model):
    """Store notifications sent to users"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('read', 'Read'),
    )
    
    user = models.ForeignKey('core.User', on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    message = models.TextField()
    action_url = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    channel = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # For email notifications
    email_subject = models.CharField(max_length=255, blank=True)
    
    # For retry logic
    retry_count = models.IntegerField(default=0)
    next_retry = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['created_at']),
        ]
```

### 2. Email Service Integration (2 days)

```python
# apps/notifications/services/email_service.py
class EmailService:
    @staticmethod
    def send_email(to_email, subject, template_name, context, from_email=None):
        """Send HTML email with plain text fallback"""
        if not from_email:
            from_email = settings.DEFAULT_FROM_EMAIL
            
        # Render HTML content from template
        html_content = render_to_string(template_name, context)
        text_content = strip_tags(html_content)
        
        try:
            # Create email message
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=[to_email]
            )
            
            email.attach_alternative(html_content, "text/html")
            sent = email.send()
            
            return sent == 1
        except Exception as e:
            logger.error(f"Email sending error: {str(e)}")
            return False
    
    @staticmethod
    def send_notification_email(notification):
        """Send email for a notification object"""
        if not notification.user.email:
            logger.warning(f"Cannot send email - no address for user {notification.user.id}")
            return False
            
        subject = notification.email_subject or notification.title
        
        context = {
            'user': notification.user,
            'title': notification.title,
            'message': notification.message,
            'action_url': notification.action_url,
            'site_name': settings.SITE_NAME,
            'site_url': settings.SITE_URL,
        }
        
        template_name = f"emails/{notification.notification_type}.html"
        
        return EmailService.send_email(
            to_email=notification.user.email,
            subject=subject,
            template_name=template_name,
            context=context
        )
```

### 3. Notification Tasks & Processing (2 days)

```python
# apps/notifications/tasks.py
@shared_task
def send_notification(notification_id):
    """Process a single notification"""
    try:
        notification = Notification.objects.get(id=notification_id)
        
        # Skip if already sent
        if notification.status in ['sent', 'read']:
            return f"Notification {notification_id} already processed"
        
        success = False
        
        # Process based on channel
        if notification.channel == 'email':
            success = EmailService.send_notification_email(notification)
        elif notification.channel == 'in_app':
            # In-app notifications don't need sending
            success = True
        
        if success:
            notification.status = 'sent'
            notification.sent_at = timezone.now()
            notification.save()
            return f"Notification {notification_id} sent successfully"
        else:
            # Handle retry logic
            notification.retry_count += 1
            
            # Exponential backoff: 5min, 25min, 125min, etc.
            retry_minutes = 5 ** (min(notification.retry_count, 4))
            notification.next_retry = timezone.now() + timedelta(minutes=retry_minutes)
            
            if notification.retry_count >= 5:
                notification.status = 'failed'
                
            notification.save()
            return f"Failed to send notification {notification_id}, retry: {notification.retry_count}"
    except Exception as e:
        logger.exception(f"Error sending notification: {str(e)}")
        return f"Error: {str(e)}"

@shared_task
def process_pending_notifications():
    """Process all pending notifications"""
    now = timezone.now()
    
    # Find notifications ready to send
    notifications = Notification.objects.filter(
        status='pending'
    ).filter(
        models.Q(next_retry__isnull=True) | models.Q(next_retry__lte=now)
    )[:100]  # Batch size
    
    for notification in notifications:
        send_notification.delay(notification.id)
        
    return f"Queued {notifications.count()} notifications"
```

### 4. Notification API Endpoints (2 days)

```python
# apps/notifications/serializers.py
class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ['id', 'notification_type', 'channel', 'enabled']
        read_only_fields = ['id']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'notification_type', 'title', 'message', 
                 'action_url', 'status', 'channel', 'created_at', 
                 'sent_at', 'read_at']
        read_only_fields = fields

# apps/notifications/views.py
class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    filterset_fields = ['status', 'notification_type', 'channel']
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a notification as read"""
        notification = self.get_object()
        
        if notification.status not in ['read']:
            notification.status = 'read'
            notification.read_at = timezone.now()
            notification.save()
            
        return Response(self.get_serializer(notification).data)
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        unread = Notification.objects.filter(
            user=request.user, 
            status__in=['sent', 'pending']
        )
        
        count = unread.count()
        
        now = timezone.now()
        unread.update(status='read', read_at=now)
        
        return Response({'marked_read': count})

class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    
    def get_queryset(self):
        return NotificationPreference.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
```

### 5. Production Settings (1 day)

```python
# config/settings/production.py
from .base import *

# Security settings
DEBUG = False
ALLOWED_HOSTS = ['pollarize.pythonanywhere.com', os.environ.get('SITE_DOMAIN', '')]

# HTTPS settings
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Database settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME', ''),
        'USER': os.environ.get('DB_USER', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', ''),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# Cache settings
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://localhost:6379/1'),
    }
}

# REST Framework throttling
REST_FRAMEWORK = {
    # ... existing settings
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    },
}

# CORS settings
CORS_ALLOWED_ORIGINS = [
    'https://yourdomain.com',
]
CORS_ALLOW_CREDENTIALS = True

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': '/var/log/pollarize/django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### 6. Deployment Configuration (1 day)

```python
# deployment/wsgi.py
"""
WSGI config for deployment to PythonAnywhere
"""
import os
import sys

# Add project directory to Python path
path = '/home/yourusername/pollarize'
if path not in sys.path:
    sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.production'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# deployment/task_runner.py (for free tier)
"""
Script to process tasks in free-tier environments
To be run as a scheduled task
"""
import os
import django
import logging
from datetime import datetime

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from apps.notifications.tasks import process_pending_notifications
from apps.analytics.tasks import update_poll_analytics

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='/home/yourusername/pollarize/logs/tasks.log',
)

logger = logging.getLogger(__name__)

def run_scheduled_tasks():
    """Run tasks that would normally be handled by Celery"""
    start_time = datetime.now()
    logger.info(f"Starting scheduled tasks at {start_time}")
    
    # Process notifications
    try:
        process_pending_notifications()
    except Exception as e:
        logger.error(f"Error processing notifications: {str(e)}")
    
    # Run analytics updates
    try:
        update_poll_analytics()
    except Exception as e:
        logger.error(f"Error updating analytics: {str(e)}")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    logger.info(f"Completed scheduled tasks in {duration:.2f} seconds")

if __name__ == "__main__":
    run_scheduled_tasks()
```

### 7. Health Check & Monitoring (1 day)

```python
# apps/core/views.py
class HealthCheckView(APIView):
    """
    API endpoint for system health monitoring
    """
    permission_classes = []  # Public endpoint
    
    def get(self, request, format=None):
        # Check database connection
        db_healthy = True
        try:
            connections['default'].cursor()
        except OperationalError:
            db_healthy = False
        
        # Check Redis connection
        cache_healthy = True
        try:
            cache.set('health_check', 'ok', 10)
            cache_result = cache.get('health_check')
            if cache_result != 'ok':
                cache_healthy = False
        except:
            cache_healthy = False
        
        # Overall status
        status_code = status.HTTP_200_OK
        if not db_healthy or not cache_healthy:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        
        # Include version info
        try:
            with open(os.path.join(os.path.dirname(__file__), '../../VERSION'), 'r') as f:
                version = f.read().strip()
        except:
            version = 'unknown'
        
        return Response({
            'status': 'healthy' if db_healthy and cache_healthy else 'unhealthy',
            'version': version,
            'database': 'connected' if db_healthy else 'disconnected',
            'cache': 'connected' if cache_healthy else 'disconnected',
            'timestamp': timezone.now().isoformat()
        }, status=status_code)

# api/v1/urls.py
urlpatterns += [
    path('health/', HealthCheckView.as_view(), name='health'),
]
```

## Performance Considerations

1. **Notification Delivery**:
   - Batch notification processing to reduce overhead
   - Implement exponential backoff for failed deliveries
   - Cache templates to reduce rendering time

2. **Production Optimizations**:
   - Configure proper connection pooling for database
   - Set cache timeouts appropriately for resources
   - Use atomic database operations for status updates

3. **Deployment Considerations**:
   - Configure static file caching with long TTLs
   - Implement database query caching for read-heavy views
   - Use proper timeouts for external service calls

## Testing Requirements

1. **Unit Tests**:
   - Test notification delivery with various channels
   - Validate preference system correctly filters notifications
   - Test email template rendering with edge cases

2. **Integration Tests**:
   - Verify end-to-end notification dispatch flow
   - Test health check endpoint with simulated failures
   - Validate production settings with security scanners

3. **Load Tests**:
   - Test notification system with batched processing
   - Validate health check under high traffic conditions
   - Test rate limiting effectiveness

## Definition of Done

- Notification preferences control notification delivery
- Email notifications correctly render and send
- Production settings correctly enforce security measures
- Health check endpoint accurately reports system status
- Deployment scripts successfully configure the application
- Scheduled tasks correctly process background operations
- All tests pass in production-like environment

---

# Phase 5: Notifications & Production Readiness

**Objective:**
Implement notification channels and prepare for production deployment with monitoring, logging, and scalable configs.

## Goals

- `Notification` model and email/push service integrations.
- DRF endpoints for notification management and user preferences.
- Celery tasks for sending email and SMS notifications.
- Production settings: security headers, CORS, rate limits, logging.
- Deployment scripts for PythonAnywhere or other free hosting.
- Monitoring and health-check endpoints.

## Deliverables

1. Models, serializers, and viewsets for notifications and preferences.
2. Email service (`email_service.py`) using Gmail SMTP or SendGrid.
3. Celery tasks for notification dispatch and retry logic.
4. Production-ready settings in `production.py` with secure defaults.
5. Infrastructure scripts: WSGI config, static/media setup, scheduled tasks.
6. Dashboard or endpoint for health checks and logs.
7. Tests for notification workflows and production configs.

## AI Agent Tasks

- Generate `Notification` model, migrations, and serializers.
- Scaffold email service and tasks for dispatch with retry.
- Create DRF endpoints for listing, marking read, and preferences.
- Update settings for production: security, CORS, throttling.
- Write Celery configuration and scheduled tasks.
- Create deployment scripts and documentation.
- Write integration tests for notifications and production readiness.

---

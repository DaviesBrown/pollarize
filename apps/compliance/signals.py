from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from apps.polls.models import VoteSession
from .models import ComplianceLog
from .services import ComplianceService, GeolocationService


@receiver(post_save, sender=ComplianceLog)
def handle_compliance_log_creation(sender, instance, created, **kwargs):
    """Handle actions after compliance log creation"""
    if created and instance.status == 'blocked':
        # You could add additional actions here like:
        # - Send alerts for multiple blocks from same IP
        # - Update security metrics
        # - Trigger fraud detection workflows
        pass


@receiver(user_logged_in)
def track_user_login_location(sender, user, request, **kwargs):
    """Track user login locations for compliance"""
    try:
        compliance_service = ComplianceService()
        ip_address = compliance_service.get_client_ip(request)

        # Get location data
        geo_service = GeolocationService()
        location_data = geo_service.get_location_data(ip_address)

        # Log the login event
        compliance_service.log_compliance_action(
            action='user_login',
            user=user,
            ip_address=ip_address,
            country_code=location_data.get('country_code', 'XX'),
            status='allowed',
            reason='User login tracked',
            metadata=location_data,
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

    except Exception as e:
        # Don't break login flow for compliance tracking errors
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to track login location: {e}")


@receiver(post_save, sender=VoteSession)
def update_session_geolocation(sender, instance, created, **kwargs):
    """Update vote session with geolocation data"""
    if created and not instance.country_code:
        try:
            geo_service = GeolocationService()
            location_data = geo_service.get_location_data(instance.ip_address)

            # Update the session with country code
            instance.country_code = location_data.get('country_code', 'XX')
            instance.save(update_fields=['country_code'])

        except Exception as e:
            # Don't break the voting flow
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to update session geolocation: {e}")

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def update_poll_analytics(self, poll_id=None):
    """Update analytics for a specific poll or all active polls"""
    try:
        from .services import AnalyticsService

        analytics_service = AnalyticsService()
        success = analytics_service.update_poll_analytics(poll_id)

        if success:
            logger.info(
                f"Successfully updated poll analytics for poll_id: {poll_id}")
            return {"status": "success", "poll_id": poll_id}
        else:
            raise Exception("Analytics update failed")

    except Exception as exc:
        logger.error(f"Error updating poll analytics: {exc}")
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@shared_task(bind=True, max_retries=3)
def update_user_analytics(self, user_id=None):
    """Update analytics for a specific user or all active users"""
    try:
        from .services import AnalyticsService

        analytics_service = AnalyticsService()
        success = analytics_service.update_user_analytics(user_id)

        if success:
            logger.info(
                f"Successfully updated user analytics for user_id: {user_id}")
            return {"status": "success", "user_id": user_id}
        else:
            raise Exception("User analytics update failed")

    except Exception as exc:
        logger.error(f"Error updating user analytics: {exc}")
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@shared_task(bind=True, max_retries=2)
def create_analytics_snapshot(self, snapshot_type='daily'):
    """Create analytics snapshot for trend analysis"""
    try:
        from .services import AnalyticsService

        analytics_service = AnalyticsService()
        success = analytics_service.create_snapshot(snapshot_type)

        if success:
            logger.info(
                f"Successfully created {snapshot_type} analytics snapshot")
            return {"status": "success", "snapshot_type": snapshot_type}
        else:
            raise Exception("Snapshot creation failed")

    except Exception as exc:
        logger.error(f"Error creating analytics snapshot: {exc}")
        raise self.retry(exc=exc, countdown=300)  # 5 minute delay


@shared_task
def cleanup_old_analytics_events():
    """Clean up old analytics events based on retention policy"""
    try:
        from django.conf import settings
        from .models import AnalyticsEvent

        retention_days = getattr(settings, 'ANALYTICS_RETENTION_DAYS', 365)
        cutoff_date = timezone.now() - timedelta(days=retention_days)

        deleted_count = AnalyticsEvent.objects.filter(
            created_at__lt=cutoff_date
        ).delete()[0]

        logger.info(f"Cleaned up {deleted_count} old analytics events")
        return {"status": "success", "deleted_count": deleted_count}

    except Exception as exc:
        logger.error(f"Error cleaning up analytics events: {exc}")
        return {"status": "error", "error": str(exc)}


@shared_task
def aggregate_hourly_analytics():
    """Aggregate analytics data every hour"""
    try:
        from .services import AnalyticsService

        analytics_service = AnalyticsService()

        # Create hourly snapshot
        snapshot_success = analytics_service.create_snapshot('hourly')

        # Update real-time analytics for active polls
        from apps.polls.models import Poll
        active_polls = Poll.objects.filter(is_active=True)[
            :100]  # Limit to prevent overload

        updated_count = 0
        for poll in active_polls:
            success = analytics_service.update_poll_analytics(poll.id)
            if success:
                updated_count += 1

        logger.info(
            f"Hourly aggregation: snapshot={snapshot_success}, polls_updated={updated_count}")

        return {
            "status": "success",
            "snapshot_created": snapshot_success,
            "polls_updated": updated_count
        }

    except Exception as exc:
        logger.error(f"Error in hourly analytics aggregation: {exc}")
        return {"status": "error", "error": str(exc)}


@shared_task
def track_analytics_event(event_type, user_id=None, poll_id=None,
                          ip_address='', country_code='', device_type='unknown',
                          metadata=None):
    """Asynchronously track an analytics event"""
    try:
        from .services import AnalyticsService
        from django.contrib.auth import get_user_model
        from apps.polls.models import Poll

        User = get_user_model()
        analytics_service = AnalyticsService()

        # Get user and poll objects
        user = None
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                pass

        poll = None
        if poll_id:
            try:
                poll = Poll.objects.get(id=poll_id)
            except Poll.DoesNotExist:
                pass

        # Track the event
        event = analytics_service.track_event(
            event_type=event_type,
            user=user,
            poll=poll,
            ip_address=ip_address,
            country_code=country_code,
            device_type=device_type,
            metadata=metadata or {}
        )

        if event:
            logger.info(
                f"Successfully tracked {event_type} event for user_id: {user_id}, poll_id: {poll_id}")
            return {"status": "success", "event_id": event.id}
        else:
            raise Exception("Event tracking failed")

    except Exception as exc:
        logger.error(f"Error tracking analytics event: {exc}")
        return {"status": "error", "error": str(exc)}

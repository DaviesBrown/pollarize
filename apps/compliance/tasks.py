from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_geolocation_cache():
    """Clean up expired geolocation cache entries"""
    try:
        from .models import GeolocationCache

        deleted_count = GeolocationCache.objects.filter(
            expires_at__lt=timezone.now()
        ).delete()[0]

        logger.info(
            f"Cleaned up {deleted_count} expired geolocation cache entries")
        return {"status": "success", "deleted_count": deleted_count}

    except Exception as exc:
        logger.error(f"Error cleaning up geolocation cache: {exc}")
        return {"status": "error", "error": str(exc)}


@shared_task
def cleanup_old_compliance_logs():
    """Clean up old compliance logs based on retention policy"""
    try:
        from django.conf import settings
        from .models import ComplianceLog

        retention_days = getattr(
            settings, 'COMPLIANCE_LOG_RETENTION_DAYS', 180)
        cutoff_date = timezone.now() - timedelta(days=retention_days)

        deleted_count = ComplianceLog.objects.filter(
            created_at__lt=cutoff_date
        ).delete()[0]

        logger.info(f"Cleaned up {deleted_count} old compliance logs")
        return {"status": "success", "deleted_count": deleted_count}

    except Exception as exc:
        logger.error(f"Error cleaning up compliance logs: {exc}")
        return {"status": "error", "error": str(exc)}


@shared_task(bind=True, max_retries=3)
def perform_compliance_check(self, poll_id, user_id=None, ip_address=''):
    """Asynchronously perform compliance checks"""
    try:
        from .services import ComplianceService
        from apps.polls.models import Poll
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # Get objects
        try:
            poll = Poll.objects.get(id=poll_id)
        except Poll.DoesNotExist:
            raise Exception(f"Poll with id {poll_id} not found")

        user = None
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                pass

        compliance_service = ComplianceService()

        # Perform checks
        geo_result = compliance_service.check_geographic_restrictions(
            poll=poll,
            ip_address=ip_address,
            user=user
        )

        voting_result = compliance_service.check_voting_limits(
            poll=poll,
            user=user,
            ip_address=ip_address
        )

        result = {
            "status": "success",
            "poll_id": poll_id,
            "user_id": user_id,
            "geographic_check": geo_result,
            "voting_check": voting_result,
            "overall_allowed": not (geo_result['blocked'] or voting_result['blocked'])
        }

        logger.info(
            f"Compliance check completed for poll_id: {poll_id}, user_id: {user_id}")
        return result

    except Exception as exc:
        logger.error(f"Error in compliance check: {exc}")
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@shared_task
def generate_compliance_report(date_from=None, date_to=None):
    """Generate compliance report for a given date range"""
    try:
        from .models import ComplianceLog
        from django.db.models import Count

        if not date_from:
            date_from = timezone.now() - timedelta(days=7)
        if not date_to:
            date_to = timezone.now()

        queryset = ComplianceLog.objects.filter(
            created_at__gte=date_from,
            created_at__lte=date_to
        )

        # Generate statistics
        total_logs = queryset.count()
        blocked_requests = queryset.filter(status='blocked').count()
        allowed_requests = queryset.filter(status='allowed').count()
        flagged_requests = queryset.filter(status='flagged').count()

        # Top blocked countries
        top_blocked_countries = list(
            queryset.filter(status='blocked')
            .values('country_code')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        # Top blocked actions
        top_blocked_actions = list(
            queryset.filter(status='blocked')
            .values('action')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        report = {
            "status": "success",
            "period": {
                "from": date_from.isoformat(),
                "to": date_to.isoformat()
            },
            "summary": {
                "total_logs": total_logs,
                "blocked_requests": blocked_requests,
                "allowed_requests": allowed_requests,
                "flagged_requests": flagged_requests,
                "block_rate": round((blocked_requests / max(total_logs, 1)) * 100, 2)
            },
            "top_blocked_countries": top_blocked_countries,
            "top_blocked_actions": top_blocked_actions
        }

        logger.info(
            f"Generated compliance report for period {date_from} to {date_to}")
        return report

    except Exception as exc:
        logger.error(f"Error generating compliance report: {exc}")
        return {"status": "error", "error": str(exc)}


@shared_task
def update_geolocation_data(ip_addresses):
    """Batch update geolocation data for multiple IP addresses"""
    try:
        from .services import GeolocationService

        geo_service = GeolocationService()
        updated_count = 0

        for ip_address in ip_addresses:
            try:
                location_data = geo_service.get_location_data(ip_address)
                if location_data and not location_data.get('cached'):
                    updated_count += 1
            except Exception as e:
                logger.warning(
                    f"Failed to update geolocation for {ip_address}: {e}")
                continue

        logger.info(
            f"Updated geolocation data for {updated_count} IP addresses")
        return {"status": "success", "updated_count": updated_count}

    except Exception as exc:
        logger.error(f"Error updating geolocation data: {exc}")
        return {"status": "error", "error": str(exc)}

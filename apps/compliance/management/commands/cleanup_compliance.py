from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
from apps.compliance.models import ComplianceLog, GeolocationCache


class Command(BaseCommand):
    help = 'Cleanup old compliance data and cache entries'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=180,
            help='Number of days to retain compliance logs (default: 180)',
        )
        parser.add_argument(
            '--logs-only',
            action='store_true',
            help='Only clean up compliance logs',
        )
        parser.add_argument(
            '--cache-only',
            action='store_true',
            help='Only clean up expired geolocation cache',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        try:
            if not options['cache_only']:
                self.cleanup_compliance_logs(options)

            if not options['logs_only']:
                self.cleanup_geolocation_cache(options)

        except Exception as e:
            raise CommandError(f'Cleanup failed: {str(e)}')

    def cleanup_compliance_logs(self, options):
        """Clean up old compliance logs"""
        retention_days = options['days']
        cutoff_date = timezone.now() - timedelta(days=retention_days)

        old_logs = ComplianceLog.objects.filter(created_at__lt=cutoff_date)
        count = old_logs.count()

        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would delete {count} compliance logs older than {retention_days} days'
                )
            )
        else:
            if count > 0:
                deleted_count = old_logs.delete()[0]
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully deleted {deleted_count} old compliance logs'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('No old compliance logs to delete')
                )

    def cleanup_geolocation_cache(self, options):
        """Clean up expired geolocation cache entries"""
        expired_cache = GeolocationCache.objects.filter(
            expires_at__lt=timezone.now()
        )
        count = expired_cache.count()

        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would delete {count} expired geolocation cache entries'
                )
            )
        else:
            if count > 0:
                deleted_count = expired_cache.delete()[0]
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully deleted {deleted_count} expired cache entries'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('No expired cache entries to delete')
                )

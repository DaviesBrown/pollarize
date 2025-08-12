from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from apps.analytics.services import AnalyticsService


class Command(BaseCommand):
    help = 'Update analytics data for polls and users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--poll-id',
            type=int,
            help='Update analytics for a specific poll ID',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='Update analytics for a specific user ID',
        )
        parser.add_argument(
            '--all-polls',
            action='store_true',
            help='Update analytics for all active polls',
        )
        parser.add_argument(
            '--all-users',
            action='store_true',
            help='Update analytics for all active users',
        )
        parser.add_argument(
            '--create-snapshot',
            choices=['hourly', 'daily', 'weekly', 'monthly'],
            help='Create analytics snapshot',
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up old analytics events',
        )

    def handle(self, *args, **options):
        analytics_service = AnalyticsService()

        try:
            if options['poll_id']:
                self.stdout.write(
                    f"Updating analytics for poll ID: {options['poll_id']}")
                success = analytics_service.update_poll_analytics(
                    options['poll_id'])
                if success:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Successfully updated poll analytics')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR('Failed to update poll analytics')
                    )

            elif options['user_id']:
                self.stdout.write(
                    f"Updating analytics for user ID: {options['user_id']}")
                success = analytics_service.update_user_analytics(
                    options['user_id'])
                if success:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Successfully updated user analytics')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR('Failed to update user analytics')
                    )

            elif options['all_polls']:
                self.stdout.write("Updating analytics for all active polls...")
                success = analytics_service.update_poll_analytics()
                if success:
                    self.stdout.write(
                        self.style.SUCCESS(
                            'Successfully updated all poll analytics')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR('Failed to update poll analytics')
                    )

            elif options['all_users']:
                self.stdout.write("Updating analytics for all active users...")
                success = analytics_service.update_user_analytics()
                if success:
                    self.stdout.write(
                        self.style.SUCCESS(
                            'Successfully updated all user analytics')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR('Failed to update user analytics')
                    )

            elif options['create_snapshot']:
                snapshot_type = options['create_snapshot']
                self.stdout.write(
                    f"Creating {snapshot_type} analytics snapshot...")
                success = analytics_service.create_snapshot(snapshot_type)
                if success:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Successfully created {snapshot_type} snapshot')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Failed to create {snapshot_type} snapshot')
                    )

            elif options['cleanup']:
                self.stdout.write("Cleaning up old analytics events...")
                from django.conf import settings
                from datetime import timedelta
                from apps.analytics.models import AnalyticsEvent

                retention_days = getattr(
                    settings, 'ANALYTICS_RETENTION_DAYS', 365)
                cutoff_date = timezone.now() - timedelta(days=retention_days)

                deleted_count = AnalyticsEvent.objects.filter(
                    created_at__lt=cutoff_date
                ).delete()[0]

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Cleaned up {deleted_count} old analytics events')
                )

            else:
                self.stdout.write(
                    self.style.WARNING(
                        'No action specified. Use --help for available options.')
                )

        except Exception as e:
            raise CommandError(f'Analytics update failed: {str(e)}')

from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Initialize the application with required setup'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-migrations',
            action='store_true',
            help='Skip running migrations',
        )
        parser.add_argument(
            '--skip-cache',
            action='store_true',
            help='Skip creating cache table',
        )

    def handle(self, *args, **options):
        """Initialize the application"""

        self.stdout.write(
            self.style.SUCCESS('🚀 Initializing Pollarize API...\n')
        )

        try:
            # Create cache table for database caching
            if not options['skip_cache']:
                self.stdout.write('Creating cache table...')
                call_command('createcachetable')
                self.stdout.write(
                    self.style.SUCCESS('✓ Cache table created\n')
                )

            # Run migrations
            if not options['skip_migrations']:
                self.stdout.write('Running migrations...')
                call_command('migrate')
                self.stdout.write(
                    self.style.SUCCESS('✓ Migrations completed\n')
                )

            # Update analytics for existing data
            self.stdout.write('Setting up analytics...')
            try:
                from apps.analytics.services import AnalyticsService
                analytics_service = AnalyticsService()

                # Create analytics records for existing polls and users
                from apps.polls.models import Poll
                from django.contrib.auth import get_user_model
                from apps.analytics.models import PollAnalytics, UserAnalytics

                User = get_user_model()

                # Create poll analytics
                for poll in Poll.objects.all():
                    PollAnalytics.objects.get_or_create(poll=poll)

                # Create user analytics
                for user in User.objects.all():
                    UserAnalytics.objects.get_or_create(user=user)

                self.stdout.write(
                    self.style.SUCCESS('✓ Analytics setup completed\n')
                )

            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'⚠ Analytics setup failed: {e}\n')
                )

            self.stdout.write(
                self.style.SUCCESS(
                    '🎉 Initialization completed successfully!\n')
            )

            self.stdout.write('Next steps:')
            self.stdout.write(
                '1. Create a superuser: python manage.py createsuperuser')
            self.stdout.write(
                '2. Collect static files: python manage.py collectstatic')
            self.stdout.write('3. Test your API endpoints')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Initialization failed: {e}')
            )

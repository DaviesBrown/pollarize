from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection
import os


class Command(BaseCommand):
    help = 'Verify deployment configuration for PythonAnywhere'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Pollarize Deployment Verification\n')
        )

        # Check Django settings
        self.stdout.write('📋 Configuration Check:')
        self.stdout.write(
            f'  ✓ Django Version: {settings.__dict__.get("DJANGO_VERSION", "Unknown")}')
        self.stdout.write(f'  ✓ Debug Mode: {settings.DEBUG}')
        self.stdout.write(
            f'  ✓ Secret Key: {"Set" if settings.SECRET_KEY else "❌ NOT SET"}')
        self.stdout.write(f'  ✓ Allowed Hosts: {settings.ALLOWED_HOSTS}')

        # Check database
        self.stdout.write('\n🗄️  Database Check:')
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM django_migrations")
                migrations_count = cursor.fetchone()[0]
                self.stdout.write(
                    f'  ✓ Database Connected: {connection.vendor}')
                self.stdout.write(
                    f'  ✓ Migrations Applied: {migrations_count}')
        except Exception as e:
            self.stdout.write(f'  ❌ Database Error: {e}')

        # Check API keys
        self.stdout.write('\n🔑 API Keys Check:')
        paystack_public = getattr(settings, 'PAYSTACK_PUBLIC_KEY', '')
        paystack_secret = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
        self.stdout.write(
            f'  ✓ Paystack Public Key: {"Set" if paystack_public else "❌ NOT SET"}')
        self.stdout.write(
            f'  ✓ Paystack Secret Key: {"Set" if paystack_secret else "❌ NOT SET"}')

        # Check static files
        self.stdout.write('\n📁 Static Files Check:')
        self.stdout.write(f'  ✓ Static URL: {settings.STATIC_URL}')
        self.stdout.write(f'  ✓ Static Root: {settings.STATIC_ROOT}')

        if os.path.exists(settings.STATIC_ROOT):
            file_count = len([f for f in os.listdir(settings.STATIC_ROOT)
                              if os.path.isfile(os.path.join(settings.STATIC_ROOT, f))])
            self.stdout.write(
                f'  ✓ Static Files Collected: {file_count} files')
        else:
            self.stdout.write(
                '  ❌ Static files not collected. Run: python manage.py collectstatic')

        # Check celery configuration
        self.stdout.write('\n⚙️  Celery Check:')
        celery_eager = getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False)
        self.stdout.write(
            f'  ✓ Always Eager (for PythonAnywhere): {celery_eager}')

        # Check installed apps
        self.stdout.write('\n📦 Apps Check:')
        required_apps = [
            'apps.core', 'apps.polls', 'apps.payments',
            'apps.analytics', 'apps.compliance'
        ]
        for app in required_apps:
            if app in settings.INSTALLED_APPS:
                self.stdout.write(f'  ✓ {app}')
            else:
                self.stdout.write(f'  ❌ {app} - NOT INSTALLED')

        # Final recommendations
        self.stdout.write('\n🎯 PythonAnywhere Free Plan Compatibility:')

        if settings.DEBUG:
            self.stdout.write('  ⚠️  Set DEBUG=False for production')
        else:
            self.stdout.write('  ✓ DEBUG disabled for production')

        if celery_eager:
            self.stdout.write(
                '  ✓ Celery configured for synchronous execution')
        else:
            self.stdout.write('  ⚠️  Set CELERY_ALWAYS_EAGER=1 for free plan')

        if 'sqlite' in str(settings.DATABASES['default']['ENGINE']):
            self.stdout.write('  ✓ Using SQLite (free plan compatible)')
        else:
            self.stdout.write(
                '  ⚠️  Using external database (requires paid plan)')

        self.stdout.write('\n✅ Verification complete!')
        self.stdout.write('\n📚 Next steps:')
        self.stdout.write(
            '   1. Set your Paystack API keys in environment variables')
        self.stdout.write('   2. Run: python manage.py collectstatic')
        self.stdout.write('   3. Configure your PythonAnywhere web app')
        self.stdout.write('   4. Set proper ALLOWED_HOSTS for your domain')

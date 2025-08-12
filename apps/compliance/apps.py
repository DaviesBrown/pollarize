from django.apps import AppConfig


class ComplianceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.compliance'
    verbose_name = 'Compliance'

    def ready(self):
        """Import signals when the app is ready"""
        try:
            import apps.compliance.signals  # noqa
        except ImportError:
            pass

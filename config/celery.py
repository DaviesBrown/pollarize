import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('pollarize')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


# Optional: Configure Celery for PythonAnywhere
# Since PythonAnywhere free tier doesn't support background workers,
# you can run tasks synchronously for development
if os.environ.get('CELERY_ALWAYS_EAGER', '0') == '1':
    app.conf.task_always_eager = True
    app.conf.task_eager_propagates = True

from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab
import tasks

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Define periodic task schedule
app.conf.beat_schedule = {
    'send-summary-every-12-hours': {
        'task': 'tasks.celery.send_summary_pdfs',  # Make sure this is your full task path
        'schedule': crontab(minute=0, hour='0,12'),  # Run at midnight and noon
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

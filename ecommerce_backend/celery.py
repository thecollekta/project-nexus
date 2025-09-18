# ecommerce_backend/celery.py

import os

from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "ecommerce_backend.settings.development"
)

app = Celery("ecommerce_backend")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# Windows-specific settings
if os.name == "nt":
    # Use threads instead of processes on Windows
    app.conf.worker_pool = "solo"  # or 'threads' for newer Celery versions
    app.conf.worker_concurrency = 1  # Reduce concurrency on Windows

# Configure periodic tasks (beat schedule)
app.conf.beat_schedule = {
    # Add your periodic tasks here as needed
}

# Configure timezone
app.conf.timezone = settings.TIME_ZONE

# Add retry configuration
app.conf.task_acks_late = True
app.conf.task_reject_on_worker_lost = True
app.conf.worker_prefetch_multiplier = 1

# Logging configuration
app.conf.worker_log_format = "[%(asctime)s: %(levelname)s/%(processName)s] %(message)s"
app.conf.worker_redirect_stdouts = False


@app.task(bind=True)
def debug_task(self):
    pass

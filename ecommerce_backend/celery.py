# ecommerce_backend/celery.py

import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ecommerce_backend.settings.production")

app = Celery("ecommerce_backend")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Windows-specific settings
if os.name == "nt":
    app.conf.worker_pool = "solo"
    app.conf.worker_concurrency = 1

# Configure periodic tasks
app.conf.beat_schedule = {
    # Add your periodic tasks here
    "cleanup-expired-carts": {
        "task": "apps.orders.tasks.cleanup_expired_carts",
        "schedule": 3600.0,  # Run every hour
    },
    "update-order-statuses": {
        "task": "apps.orders.tasks.update_order_statuses",
        "schedule": 1800.0,  # Run every 30 minutes
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")

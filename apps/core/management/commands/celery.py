# apps/core/management/commands/celery.py

import os
import signal
import sys
from subprocess import Popen

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Start Celery worker and beat processes"

    def add_arguments(self, parser):
        parser.add_argument(
            "--loglevel",
            default="info",
            help="Log level (debug, info, warning, error, critical)",
        )
        parser.add_argument(
            "--concurrency",
            type=int,
            default=1,  # Default to 1 for Windows
            help="Number of worker processes/threads (1 recommended for Windows)",
        )

    def handle(self, *args, **options):
        loglevel = options["loglevel"]
        concurrency = options["concurrency"]

        # Windows-specific settings
        if os.name == "nt":
            worker_pool = "solo"  # Use solo pool for Windows
            self.stdout.write(
                self.style.WARNING("Windows detected: Using 'solo' worker pool")
            )
        else:
            worker_pool = "prefork"

        # Start Celery worker
        worker_cmd = [
            "celery",
            "-A",
            "ecommerce_backend",
            "worker",
            f"--loglevel={loglevel}",
            f"--concurrency={concurrency}",
            f"--pool={worker_pool}",
            "--hostname=worker1@%h",
        ]

        # Start Celery beat
        beat_cmd = [
            "celery",
            "-A",
            "ecommerce_backend",
            "beat",
            f"--loglevel={loglevel}",
            "--scheduler",
            "django_celery_beat.schedulers:DatabaseScheduler",
        ]

        processes = []

        def signal_handler(sig, frame):
            self.stdout.write(self.style.WARNING("Stopping Celery processes..."))
            for p in processes:
                p.terminate()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            self.stdout.write(self.style.SUCCESS("Starting Celery worker..."))
            worker_process = Popen(worker_cmd)  # noqa: S603
            processes.append(worker_process)

            self.stdout.write(self.style.SUCCESS("Starting Celery beat..."))
            beat_process = Popen(beat_cmd)  # noqa: S603
            processes.append(beat_process)

            # Keep the command running
            for p in processes:
                p.wait()

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error: {e}"))
            for p in processes:
                p.terminate()
            sys.exit(1)

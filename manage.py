#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys

# Conditional import for coverage (development only)
HAS_COVERAGE = False
try:
    import coverage

    HAS_COVERAGE = True
except ImportError:
    pass


def main():
    """Run administrative tasks."""
    # Default to development, but allow environment variable override
    settings_module = os.environ.get(
        "DJANGO_SETTINGS_MODULE", "ecommerce_backend.settings.development"
    )
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # Only run tests automatically in development mode
    is_development = settings_module.endswith(".development")

    if len(sys.argv) == 1 and is_development and HAS_COVERAGE:
        # Development mode with coverage - run tests
        print("Development mode detected: Running tests with coverage...")
        cov = coverage.Coverage()
        cov.start()

        test_args = [
            "manage.py",
            "test",
            "tests/unit/accounts/test_accounts.py",
            "-v",
            "2",
        ]
        execute_from_command_line(test_args)

        cov.stop()
        cov.save()
        cov.report(show_missing=True)
        cov.html_report(directory="htmlcov")
    elif len(sys.argv) == 1 and is_development:
        # Development mode without coverage
        print("Development mode detected: Running tests...")
        test_args = [
            "manage.py",
            "test",
            "tests/unit/accounts/test_accounts.py",
            "-v",
            "2",
        ]
        execute_from_command_line(test_args)
    elif len(sys.argv) == 1:
        # Production mode - show help instead of running tests
        print(
            "Production mode: Use specific commands like 'migrate', 'collectstatic', etc."
        )
        print("Available commands: migrate, collectstatic, createsuperuser, etc.")
        execute_from_command_line([sys.argv[0], "help"])
    else:
        # Normal command execution
        execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

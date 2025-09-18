#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys

from django.core.management import execute_from_command_line

# Conditional import for coverage
HAS_COVERAGE = False
try:
    import coverage

    HAS_COVERAGE = True
except ImportError:
    pass


def main():
    """Run administrative tasks."""
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        "ecommerce_backend.settings.development",
    )

    # Run tests with coverage if coverage is installed and no arguments provided
    if len(sys.argv) == 1 and HAS_COVERAGE:
        cov = coverage.Coverage()
        cov.start()

        # Run tests
        test_args = [
            "manage.py",
            "test",
            "tests/unit/accounts/test_accounts.py",
            "-v",
            "2",
        ]
        execute_from_command_line(test_args)

        # Generate coverage report
        cov.stop()
        cov.save()
        cov.report(show_missing=True)

        # Generate HTML report
        cov.html_report(directory="htmlcov")

    elif len(sys.argv) == 1:
        # Fallback to normal test command if coverage is not installed
        test_args = [
            "manage.py",
            "test",
            "tests/unit/accounts/test_accounts.py",
            "-v",
            "2",
        ]
        execute_from_command_line(test_args)
    else:
        execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

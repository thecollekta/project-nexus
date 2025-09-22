#!/usr/bin/env bash
# render-build.sh - Build script for Render.com deployment

set -o errexit  # Exit on error
set -o pipefail # Capture pipe failures
set -o nounset  # Exit on undefined variables

echo "Starting Render.com Build Process"

# Set production settings for all management commands
export DJANGO_SETTINGS_MODULE=ecommerce_backend.settings.production

# Install dependencies
echo "--- Installing Python dependencies ---"
pip install -r requirements/production.txt

# Wait for database to be ready (optional but recommended)
echo "--- Waiting for database connectivity ---"
sleep 5

# Apply database migrations
echo "--- Applying database migrations ---"
python manage.py makemigrations --noinput || echo "No new migrations detected"
python manage.py migrate --noinput

# Collect static files
echo "--- Collecting static files ---"
python manage.py collectstatic --noinput --clear

# Create superuser using environment variables
echo "--- Setting up superuser ---"
python manage.py create_superuser_if_none

# Validate installation
echo "--- Validating Django installation ---"
python manage.py check --deploy

echo "Build completed successfully"
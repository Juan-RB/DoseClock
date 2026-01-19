#!/usr/bin/env bash
# Build script for Render

set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --noinput

# Try to run migrations, but don't fail the build if DB is not ready
python manage.py migrate --noinput || echo "Migration failed, will retry on startup"

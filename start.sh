#!/usr/bin/env bash
# Start script for Render - runs migrations then starts server

echo "==> Running migrations..."
python manage.py migrate --noinput

echo "==> Setting up initial users..."
python manage.py setup_users --admin-password "${ADMIN_PASSWORD:-Admin123!}" --user-password "${USER_PASSWORD:-Usuario123!}"

echo "==> Starting Gunicorn..."
exec gunicorn doseclock.wsgi --log-file -

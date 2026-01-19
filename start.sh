#!/usr/bin/env bash
# Start script for Render - runs migrations then starts server

echo "==> Running migrations..."
python manage.py migrate --noinput

echo "==> Starting Gunicorn..."
exec gunicorn doseclock.wsgi --log-file -

#!/bin/sh
set -e

mkdir -p /app/sportrent/logs /app/sportrent/staticfiles /app/sportrent/media

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Running migrations..."
python manage.py migrate

echo "Starting Daphne..."
exec daphne -b 0.0.0.0 -p 8000 config.asgi:application

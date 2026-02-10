#!/bin/bash
# Запуск сервера с поддержкой WebSocket (чаты в реальном времени).
# Обычный "python manage.py runserver" не обрабатывает /ws/ — используйте этот скрипт.
cd "$(dirname "$0")/../sportrent"
export DJANGO_SETTINGS_MODULE=config.settings
exec daphne -b 127.0.0.1 -p 8000 config.asgi:application

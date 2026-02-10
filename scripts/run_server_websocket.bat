@echo off
REM Запуск сервера с поддержкой WebSocket (чаты в реальном времени).
REM Обычный "python manage.py runserver" не обрабатывает /ws/ — используйте этот скрипт.
cd /d "%~dp0..\sportrent"
daphne -b 127.0.0.1 -p 8000 config.asgi:application

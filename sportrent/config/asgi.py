"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

# 1) Сначала задаём настройки и инициализируем Django (загружаем приложения).
# Иначе при импорте chat.routing -> consumers -> models получим "Apps aren't loaded yet".
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django

django.setup()

# 2) Только после setup() импортируем приложения и Channels/Django.
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from django.core.asgi import get_asgi_application

from chat.routing import websocket_urlpatterns

# Оборачиваем HTTP-приложение ASGIStaticFilesHandler, чтобы daphne мог отдавать статику (CSS/JS)
django_asgi_app = get_asgi_application()
django_asgi_app = ASGIStaticFilesHandler(django_asgi_app)

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})

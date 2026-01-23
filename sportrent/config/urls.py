"""
Главный URL конфигуратор для проекта SportRent.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Стандартная админка Django (временно, потом заменим на кастомную)
    path('django-admin/', admin.site.urls),

    # Основные разделы приложения
    path('', include('core.urls')),
    path('users/', include('users.urls')),
    path('inventory/', include('inventory.urls')),
    path('rentals/', include('rentals.urls')),
    path('reviews/', include('reviews.urls')),
    path('chat/', include('chat.urls')),
    path('admin/', include('custom_admin.urls')),
]

# Медиа файлы в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
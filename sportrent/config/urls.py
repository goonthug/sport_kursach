"""
Главный URL конфигуратор для проекта SportRent.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Стандартная админка Django
    path('django-admin/', admin.site.urls),

    # Django-шаблоны (существующий фронт)
    path('', include('core.urls')),
    path('users/', include('users.urls')),
    path('inventory/', include('inventory.urls')),
    path('rentals/', include('rentals.urls')),
    path('reviews/', include('reviews.urls')),
    path('chat/', include('chat.urls')),
    path('admin/', include('custom_admin.urls')),

    # REST API v1
    path('api/v1/', include('inventory.api_urls')),
    path('api/v1/auth/', include('users.api_urls')),
    path('api/v1/ai-search/', include('ai_search.urls')),
]

# Медиа файлы в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
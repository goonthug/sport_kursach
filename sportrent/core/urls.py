"""
URL конфигурация для core приложения.
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('terms/', views.rental_terms, name='rental_terms'),
    path('geo/save/', views.save_geo_session, name='geo_save'),
    path('geo/clear/', views.clear_geo_session, name='geo_clear'),
    path('api/geo/detect-city/', views.detect_city_view, name='geo_detect_city'),
]
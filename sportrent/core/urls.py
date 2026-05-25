"""
URL конфигурация для core приложения.
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('geo/save/', views.save_geo_session, name='geo_save'),
    path('geo/clear/', views.clear_geo_session, name='geo_clear'),
]
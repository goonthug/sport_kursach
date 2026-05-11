from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import CityViewSet, InventoryViewSet

router = DefaultRouter()
router.register('cities', CityViewSet, basename='city')
router.register('items', InventoryViewSet, basename='inventory-item')

urlpatterns = [
    path('', include(router.urls)),
]

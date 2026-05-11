"""
REST API ViewSets для инвентаря и городов.
"""

import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny

from .models import City, Inventory
from .serializers import (
    CitySerializer,
    InventoryListSerializer,
    InventoryDetailSerializer,
)


class CityViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/v1/cities/ — справочник городов, поиск по name/region."""

    queryset = City.objects.all()
    serializer_class = CitySerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'region']


class InventoryFilter(django_filters.FilterSet):
    city = django_filters.UUIDFilter(field_name='pickup_point__city__city_id')
    category = django_filters.UUIDFilter(field_name='category__category_id')
    min_price = django_filters.NumberFilter(field_name='price_per_day', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price_per_day', lookup_expr='lte')
    condition = django_filters.CharFilter(field_name='condition')

    class Meta:
        model = Inventory
        fields = ['city', 'category', 'min_price', 'max_price', 'condition']


class InventoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v1/inventory/        — список доступного инвентаря с фильтрами
    GET /api/v1/inventory/{id}/   — детали инвентаря
    Фильтры: city, category, min_price, max_price, condition
    Поиск: ?search=лыжи
    Сортировка: ?ordering=price_per_day
    """

    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = InventoryFilter
    search_fields = ['name', 'description', 'brand', 'model', 'category__name']
    ordering_fields = ['price_per_day', 'avg_rating', 'added_date', 'reviews_count']
    ordering = ['-added_date']

    def get_queryset(self):
        return Inventory.objects.select_related(
            'category', 'owner', 'pickup_point__city',
        ).prefetch_related('photos').filter(status='available')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return InventoryDetailSerializer
        return InventoryListSerializer

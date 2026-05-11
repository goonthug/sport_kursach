"""
Сериализаторы для REST API инвентаря.
"""

from rest_framework import serializers
from .models import City, PickupPoint, Inventory, SportCategory, InventoryPhoto


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ['city_id', 'name', 'region', 'lat', 'lon']


class PickupPointSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source='city.name', read_only=True)

    class Meta:
        model = PickupPoint
        fields = ['point_id', 'name', 'address', 'lat', 'lon', 'city', 'city_name', 'phone', 'is_active']


class SportCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SportCategory
        fields = ['category_id', 'name', 'description', 'icon']


class InventoryPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryPhoto
        fields = ['photo_id', 'photo_url', 'is_main', 'description']


class InventoryListSerializer(serializers.ModelSerializer):
    """Облегчённый сериализатор для списков и AI-поиска."""

    category_name = serializers.CharField(source='category.name', read_only=True)
    owner_name = serializers.CharField(source='owner.full_name', read_only=True)
    pickup_point_data = PickupPointSerializer(source='pickup_point', read_only=True)
    main_photo = serializers.SerializerMethodField()

    class Meta:
        model = Inventory
        fields = [
            'inventory_id', 'name', 'brand', 'model',
            'price_per_day', 'condition', 'status',
            'avg_rating', 'reviews_count', 'total_rentals',
            'category_name', 'owner_name',
            'pickup_point_data', 'main_photo',
        ]

    def get_main_photo(self, obj):
        photo = obj.photos.filter(is_main=True).first() or obj.photos.first()
        if not photo:
            return None
        request = self.context.get('request')
        url = photo.photo_url.url
        return request.build_absolute_uri(url) if request else url


class InventoryDetailSerializer(InventoryListSerializer):
    """Полный сериализатор для страницы детали инвентаря."""

    photos = InventoryPhotoSerializer(many=True, read_only=True)

    class Meta(InventoryListSerializer.Meta):
        fields = InventoryListSerializer.Meta.fields + [
            'description', 'min_rental_days', 'max_rental_days',
            'deposit_amount', 'added_date', 'photos',
        ]

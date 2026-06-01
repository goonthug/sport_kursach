from django.contrib import admin
from django.utils.html import format_html

from .models import City, Favorite, Inventory, InventoryPhoto, PickupPoint, SportCategory


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'category', 'status', 'price_per_day', 'owner', 'image_preview')
    list_filter = ('status', 'category', 'condition')
    search_fields = ('name', 'brand', 'model', 'description', 'owner__full_name')
    readonly_fields = ('inventory_id', 'added_date', 'avg_rating', 'total_rentals', 'reviews_count', 'image_preview_large')
    ordering = ('-added_date',)

    fieldsets = (
        ('Основная информация', {
            'fields': ('inventory_id', 'name', 'description', 'brand', 'model', 'category'),
        }),
        ('Фотография', {
            'fields': ('image', 'image_preview_large'),
        }),
        ('Цены и условия', {
            'fields': ('price_per_day', 'deposit_amount', 'condition', 'min_rental_days', 'max_rental_days'),
        }),
        ('Статус и модерация', {
            'fields': ('status', 'rejection_reason', 'added_date'),
        }),
        ('Владелец и расположение', {
            'fields': ('owner', 'manager', 'pickup_point', 'bank_account'),
        }),
        ('Статистика', {
            'fields': ('avg_rating', 'total_rentals', 'reviews_count'),
        }),
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height: 50px;" />', obj.image.url)
        return '—'
    image_preview.short_description = 'Превью'

    def image_preview_large(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-width: 400px;" />', obj.image.url)
        return 'Картинка не загружена'
    image_preview_large.short_description = 'Текущая фотография'


@admin.register(SportCategory)
class SportCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'description')
    search_fields = ('name',)


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'region', 'lat', 'lon')
    search_fields = ('name', 'region')


@admin.register(PickupPoint)
class PickupPointAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'address', 'is_active')
    list_filter = ('city', 'is_active')
    search_fields = ('name', 'address')


@admin.register(InventoryPhoto)
class InventoryPhotoAdmin(admin.ModelAdmin):
    list_display = ('inventory', 'is_main', 'uploaded_date')
    list_filter = ('is_main',)

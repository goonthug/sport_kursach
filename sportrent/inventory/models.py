"""
Модели для управления спортивным инвентарем.
"""

import uuid
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from users.models import Owner, Manager


class SportCategory(models.Model):
    """Категории спортивного инвентаря."""

    category_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, verbose_name='Название категории')
    description = models.TextField(blank=True, verbose_name='Описание')
    icon = models.CharField(max_length=50, blank=True, help_text='CSS класс иконки', verbose_name='Иконка')

    class Meta:
        db_table = 'sport_categories'
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self):
        return self.name


class Inventory(models.Model):
    """Спортивный инвентарь."""

    STATUS_CHOICES = [
        ('pending', 'Ожидает проверки'),
        ('available', 'Доступен'),
        ('rented', 'Арендован'),
        ('maintenance', 'На обслуживании'),
        ('rejected', 'Отклонен'),
    ]

    CONDITION_CHOICES = [
        ('new', 'Новое'),
        ('excellent', 'Отличное'),
        ('good', 'Хорошее'),
        ('fair', 'Удовлетворительное'),
    ]

    inventory_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='inventory_items', verbose_name='Владелец')
    manager = models.ForeignKey(Manager, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_items',
                                verbose_name='Менеджер')
    category = models.ForeignKey(SportCategory, on_delete=models.PROTECT, related_name='items',
                                 verbose_name='Категория')

    name = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(verbose_name='Описание')
    brand = models.CharField(max_length=100, blank=True, verbose_name='Бренд')
    model = models.CharField(max_length=100, blank=True, verbose_name='Модель')

    price_per_day = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)],
                                        verbose_name='Цена за день')
    condition = models.CharField(max_length=50, choices=CONDITION_CHOICES, default='good', verbose_name='Состояние')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Статус')

    added_date = models.DateTimeField(default=timezone.now, verbose_name='Дата добавления')
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True,
                                     verbose_name='Средний рейтинг')
    total_rentals = models.IntegerField(default=0, verbose_name='Всего аренд')

    # Дополнительные поля для условий аренды
    min_rental_days = models.IntegerField(default=1, validators=[MinValueValidator(1)],
                                          verbose_name='Минимум дней аренды')
    max_rental_days = models.IntegerField(default=30, validators=[MinValueValidator(1)],
                                          verbose_name='Максимум дней аренды')
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Сумма залога')

    # Поле для причины отклонения
    rejection_reason = models.TextField(blank=True, verbose_name='Причина отклонения')

    class Meta:
        db_table = 'inventory'
        verbose_name = 'Инвентарь'
        verbose_name_plural = 'Инвентарь'
        ordering = ['-added_date']
        indexes = [
            models.Index(fields=['status', 'category']),
            models.Index(fields=['owner', 'status']),
        ]

    def __str__(self):
        return f"{self.name} ({self.brand})"

    def is_available(self):
        """Проверка доступности инвентаря."""
        return self.status == 'available'


class InventoryPhoto(models.Model):
    """Фотографии инвентаря."""

    photo_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name='photos', verbose_name='Инвентарь')

    photo_url = models.ImageField(upload_to='inventory_photos/', verbose_name='Фотография')
    is_main = models.BooleanField(default=False, verbose_name='Основное фото')
    description = models.TextField(blank=True, verbose_name='Описание')
    uploaded_date = models.DateTimeField(default=timezone.now, verbose_name='Дата загрузки')

    class Meta:
        db_table = 'inventory_photos'
        verbose_name = 'Фотография инвентаря'
        verbose_name_plural = 'Фотографии инвентаря'
        ordering = ['-is_main', 'uploaded_date']

    def __str__(self):
        return f"Фото {self.inventory.name}"

    def save(self, *args, **kwargs):
        """Обеспечивает наличие только одного основного фото."""
        if self.is_main:
            # Убираем флаг is_main у других фото этого инвентаря
            InventoryPhoto.objects.filter(inventory=self.inventory, is_main=True).update(is_main=False)
        super().save(*args, **kwargs)
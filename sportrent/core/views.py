"""
Views для core приложения (главная страница и общие функции).
"""

from django.shortcuts import render
from django.db import models
from inventory.models import Inventory, SportCategory
from django.db.models import Count


def home(request):
    """
    Главная страница с каталогом доступного инвентаря.
    """
    # Получаем только доступный инвентарь с оптимизацией запросов
    inventories = Inventory.objects.filter(
        status='available'
    ).select_related('category', 'owner', 'owner__user').prefetch_related('photos')[:8]

    # Получаем категории с количеством доступных предметов
    categories = SportCategory.objects.annotate(
        item_count=Count('items', filter=models.Q(items__status='available'))
    )

    context = {
        'inventories': inventories,
        'categories': categories,
    }
    return render(request, 'core/home.html', context)


def about(request):
    """
    Страница О проекте.
    """
    return render(request, 'core/about.html')
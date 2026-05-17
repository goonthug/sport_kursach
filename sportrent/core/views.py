"""
Views для core приложения (главная страница, общие функции, geo-сессия).
"""

import json
import time
import logging

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Count, Q
from inventory.models import Inventory, SportCategory

logger = logging.getLogger('sportrent')


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
        item_count=Count('items', filter=Q(items__status='available'))
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


@require_POST
def save_geo_session(request):
    """
    AJAX: сохраняет координаты/город пользователя в Django-сессию.
    Если source='browser' и city не передан — выполняет reverse geocoding через Yandex.
    """
    try:
        data = json.loads(request.body)
        lat = float(data.get('lat') or 0)
        lon = float(data.get('lon') or 0)
        city = str(data.get('city') or '').strip()
        source = str(data.get('source') or 'ip')
        address = str(data.get('address') or '').strip()

        # Для browser-источника уточняем адрес через Yandex reverse geocoding
        if source == 'browser' and lat and lon:
            try:
                from ai_search.geocoder import reverse_geocode
                result = reverse_geocode(lat, lon)
                if result:
                    city = city or result.get('city', '')
                    address = address or result.get('address', '')
            except Exception as exc:
                logger.warning('reverse_geocode не удался: %s', exc)

        request.session['user_lat'] = lat
        request.session['user_lon'] = lon
        request.session['user_city'] = city
        request.session['user_address'] = address
        request.session['geo_source'] = source
        request.session['geo_ts'] = int(time.time())

        logger.info('Geo сессия сохранена: city=%s source=%s lat=%.4f lon=%.4f', city, source, lat, lon)
        return JsonResponse({'ok': True, 'city': city, 'address': address})

    except Exception as exc:
        logger.warning('save_geo_session ошибка: %s', exc)
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)


@require_POST
def clear_geo_session(request):
    """
    AJAX: сбрасывает geo-данные из сессии (кнопка "Обновить местоположение").
    """
    for key in ('user_lat', 'user_lon', 'user_city', 'user_address', 'geo_source', 'geo_ts'):
        request.session.pop(key, None)
    return JsonResponse({'ok': True})
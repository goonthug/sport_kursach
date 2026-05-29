"""
Views для core приложения (главная страница, общие функции, geo-сессия).
"""

import ipaddress
import json
import logging
import time

import requests as http_client

from django.core.cache import cache
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.models import Count, Q
from inventory.models import Inventory, SportCategory

logger = logging.getLogger('sportrent')


@ensure_csrf_cookie
def home(request):
    """
    Главная страница с каталогом доступного инвентаря.
    """
    inventories = Inventory.objects.filter(
        status='available'
    ).select_related('category', 'owner', 'owner__user').prefetch_related('photos')[:8]

    categories = SportCategory.objects.annotate(
        item_count=Count('items', filter=Q(items__status='available'))
    )

    # Ближайшие точки выдачи — показываем если геолокация известна
    nearest_points = []
    user_lat = request.session.get('user_lat')
    user_lon = request.session.get('user_lon')
    if user_lat and user_lon:
        try:
            from inventory.services.proximity import get_nearest_points
            nearest_points = get_nearest_points(user_lat, user_lon, limit=4, max_km=100)
        except Exception as exc:
            logger.warning('get_nearest_points ошибка: %s', exc)

    context = {
        'inventories': inventories,
        'categories': categories,
        'nearest_points': nearest_points,
    }
    return render(request, 'core/home.html', context)


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

        # При ручном вводе города подставляем координаты из справочника городов
        if source == 'manual' and city and (not lat or not lon):
            try:
                from inventory.models import City as CityModel
                city_obj = CityModel.objects.filter(name__iexact=city).first()
                if city_obj and city_obj.lat and city_obj.lon:
                    lat = float(city_obj.lat)
                    lon = float(city_obj.lon)
            except Exception as exc:
                logger.warning('Поиск координат города при manual: %s', exc)

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


def rental_terms(request):
    """Страница с условиями аренды и FAQ по штрафам (ст. 622 ГК РФ, 152-ФЗ)."""
    return render(request, 'core/rental_terms.html')


@require_POST
def clear_geo_session(request):
    """
    AJAX: сбрасывает geo-данные из сессии (кнопка "Обновить местоположение").
    """
    for key in ('user_lat', 'user_lon', 'user_city', 'user_address', 'geo_source', 'geo_ts'):
        request.session.pop(key, None)
    return JsonResponse({'ok': True})


def _extract_client_ip(request) -> str:
    """Извлекает реальный IP клиента из заголовков прокси."""
    real_ip = request.META.get('HTTP_X_REAL_IP')
    if real_ip:
        return real_ip.strip()
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def detect_city_view(request):
    """
    Серверная IP-геолокация: браузер обращается к нашему endpoint,
    Django делает HTTP-запрос к ipapi.co на сервере — нет Mixed Content,
    нет CORS. Результат кэшируется в Redis на 1 час.
    """
    _GEO_NULL = {'city': None, 'lat': None, 'lon': None}

    ip = _extract_client_ip(request)

    # Приватные IP (Docker internal, localhost) — геолокация бессмысленна
    try:
        if ipaddress.ip_address(ip).is_private:
            return JsonResponse(_GEO_NULL)
    except ValueError:
        return JsonResponse(_GEO_NULL)

    cache_key = f'geo:ip:{ip}'
    cached = cache.get(cache_key)
    if cached is not None:
        return JsonResponse(cached)

    result = dict(_GEO_NULL)
    try:
        resp = http_client.get(
            f'https://ipapi.co/{ip}/json/',
            timeout=3,
            headers={'User-Agent': 'SportRyadom/1.0'},
        )
        data = resp.json()
        if not data.get('error') and data.get('city'):
            result = {
                'city': data['city'],
                'lat': float(data['latitude']),
                'lon': float(data['longitude']),
            }
    except Exception as exc:
        logger.warning('detect_city_view: ipapi.co недоступен (%s)', exc)

    # Кэшируем даже null — чтобы не долбить ipapi.co при каждом запросе
    cache.set(cache_key, result, timeout=3600)
    return JsonResponse(result)



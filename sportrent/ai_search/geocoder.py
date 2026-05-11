"""
Геокодирование через Yandex Geocoder API.
Возвращает координаты (lat, lon) для названия города.
При отсутствии ключа или ошибке сети — возвращает None, не роняет запрос.
"""

import logging
import requests
from django.conf import settings

logger = logging.getLogger('ai_search')


def get_city_coordinates(city_name: str) -> tuple[float, float] | None:
    """
    Запрашивает координаты города через Yandex Geocoder.
    Возвращает (lat, lon) или None.
    """
    api_key = getattr(settings, 'YANDEX_GEOCODER_KEY', '')
    if not api_key:
        logger.debug('YANDEX_GEOCODER_KEY не задан, геокодирование пропущено')
        return None

    try:
        resp = requests.get(
            'https://geocode-maps.yandex.ru/1.x/',
            params={
                'apikey': api_key,
                'geocode': city_name,
                'format': 'json',
                'results': 1,
                'lang': 'ru_RU',
            },
            timeout=5,
        )
        resp.raise_for_status()

        members = resp.json()['response']['GeoObjectCollection']['featureMember']
        if not members:
            logger.info('Yandex Geocoder: город "%s" не найден', city_name)
            return None

        # Yandex возвращает "lon lat" (порядок обратный)
        pos = members[0]['GeoObject']['Point']['pos']
        lon, lat = map(float, pos.split())
        logger.info('Геокодирование "%s" → lat=%.4f lon=%.4f', city_name, lat, lon)
        return lat, lon

    except Exception as exc:
        logger.warning('Ошибка геокодирования "%s": %s', city_name, exc)
        return None

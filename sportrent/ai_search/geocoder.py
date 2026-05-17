"""
Геокодирование через Yandex Geocoder API.
Прямое: город → (lat, lon).
Обратное: (lat, lon) → {'city': ..., 'address': ...}.
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


def reverse_geocode(lat: float, lon: float) -> dict | None:
    """
    Обратное геокодирование: координаты → {'city': str, 'address': str}.
    Возвращает None при ошибке или отсутствии ключа.
    """
    api_key = getattr(settings, 'YANDEX_GEOCODER_KEY', '')
    if not api_key:
        logger.debug('YANDEX_GEOCODER_KEY не задан, обратное геокодирование пропущено')
        return None

    try:
        resp = requests.get(
            'https://geocode-maps.yandex.ru/1.x/',
            params={
                'apikey': api_key,
                'geocode': f'{lon},{lat}',  # Yandex ждёт lon,lat
                'format': 'json',
                'results': 1,
                'lang': 'ru_RU',
            },
            timeout=5,
        )
        resp.raise_for_status()

        members = resp.json()['response']['GeoObjectCollection']['featureMember']
        if not members:
            return None

        meta = members[0]['GeoObject']['metaDataProperty']['GeocoderMetaData']
        addr = meta.get('AddressDetails', {})
        country = addr.get('Country', {})
        admin_area = country.get('AdministrativeArea', {})

        # Город может быть на разных уровнях вложенности
        locality = (
            admin_area.get('Locality')
            or admin_area.get('SubAdministrativeArea', {}).get('Locality')
        )
        city = locality.get('LocalityName', '') if locality else ''

        # Улица + дом
        thoroughfare = (locality or {}).get('Thoroughfare', {})
        street = thoroughfare.get('ThoroughfareName', '')
        house = thoroughfare.get('Premise', {}).get('PremiseNumber', '')
        if street and house:
            short_addr = f'ул. {street}, {house}'
        elif street:
            short_addr = f'ул. {street}'
        else:
            short_addr = ''

        logger.info('Обратное геокодирование lat=%.4f lon=%.4f → %s, %s', lat, lon, city, short_addr)
        return {'city': city, 'address': short_addr}

    except Exception as exc:
        logger.warning('Ошибка обратного геокодирования lat=%.4f lon=%.4f: %s', lat, lon, exc)
        return None

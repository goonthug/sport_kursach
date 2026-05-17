"""
Геопространственные утилиты для поиска ближайших точек выдачи.
Использует формулу Haversine — без PostGIS, достаточно для 48 точек.
"""

import math


def haversine(lat1, lon1, lat2, lon2) -> float:
    """Расстояние между двумя точками на сфере (км)."""
    R = 6371
    phi1, phi2 = math.radians(float(lat1)), math.radians(float(lat2))
    dphi = math.radians(float(lat2) - float(lat1))
    dlambda = math.radians(float(lon2) - float(lon1))
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(min(a, 1.0)))


def get_nearest_points(lat, lon, limit: int = 5, max_km: float = 100.0) -> list[dict]:
    """
    Возвращает список ближайших активных точек выдачи с расстоянием.
    Каждый элемент: {'point': PickupPoint, 'distance_km': float}
    """
    from inventory.models import PickupPoint
    points = PickupPoint.objects.filter(is_active=True).select_related('city')
    result = []
    for pp in points:
        if pp.lat is None or pp.lon is None:
            continue
        dist = haversine(lat, lon, pp.lat, pp.lon)
        if dist <= max_km:
            result.append({'point': pp, 'distance_km': round(dist, 1)})
    result.sort(key=lambda x: x['distance_km'])
    return result[:limit]


def get_nearby_pickup_point_ids(lat, lon, radius_km: float = 20.0) -> set:
    """
    Возвращает set point_id точек выдачи в заданном радиусе.
    Используется для фильтрации: Inventory.objects.filter(pickup_point_id__in=...)
    """
    from inventory.models import PickupPoint
    points = PickupPoint.objects.filter(is_active=True).only('point_id', 'lat', 'lon')
    nearby = set()
    for pp in points:
        if pp.lat is None or pp.lon is None:
            continue
        if haversine(lat, lon, pp.lat, pp.lon) <= radius_km:
            nearby.add(pp.point_id)
    return nearby

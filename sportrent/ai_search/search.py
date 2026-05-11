"""
Поиск инвентаря в БД по разобранному запросу.
Стратегия: город → категория → цена → доступность по датам.
"""

import logging
from datetime import datetime

from django.db.models import Q

from inventory.models import Inventory, City
from .geocoder import get_city_coordinates
from .parser import ParsedSearchQuery

logger = logging.getLogger('ai_search')

MAX_RESULTS = 20


def search_inventory(parsed: ParsedSearchQuery):
    """
    Выполняет поиск доступного инвентаря по полям ParsedSearchQuery.
    Возвращает QuerySet (не более MAX_RESULTS записей).
    """
    # Если LLM не распознал ничего осмысленного — не отдаём весь каталог
    if not any([parsed.category_query, parsed.keywords, parsed.city_name,
                parsed.max_price, parsed.start_date]):
        logger.info('Пустой parsed-запрос — возвращаем пустой результат')
        return Inventory.objects.none()

    qs = Inventory.objects.select_related(
        'category', 'owner', 'pickup_point__city',
    ).prefetch_related('photos').filter(status='available')

    # Фильтр по категории / ключевым словам
    keyword = parsed.category_query or parsed.keywords
    if keyword:
        qs = qs.filter(
            Q(category__name__icontains=keyword) |
            Q(name__icontains=keyword) |
            Q(description__icontains=keyword) |
            Q(brand__icontains=keyword)
        )

    # Фильтр по городу: ищем в БД, иначе геокодируем и добавляем в справочник
    if parsed.city_name:
        # Нормализуем название для поиска (убираем множественные пробелы и лишние символы)
        city_query = parsed.city_name.strip()
        # Сначала ищем точное совпадение (без учёта регистра), потом подстроку
        city = (
            City.objects.filter(name__iexact=city_query).first()
            or City.objects.filter(name__icontains=city_query).first()
        )
        if not city:
            coords = get_city_coordinates(city_query)
            if coords:
                lat, lon = coords
                # Нормализуем название: первая буква заглавная
                normalized_name = city_query.title()
                city, created = City.objects.get_or_create(
                    name=normalized_name,
                    defaults={'lat': lat, 'lon': lon},
                )
                if not created and (not city.lat or not city.lon):
                    city.lat, city.lon = lat, lon
                    city.save(update_fields=['lat', 'lon'])
                if created:
                    logger.info('Добавлен новый город в справочник: %s', normalized_name)

        if city:
            qs = qs.filter(pickup_point__city=city)
        else:
            logger.warning('Город "%s" не найден ни в БД, ни в геокодере', parsed.city_name)

    # Фильтр по цене
    if parsed.max_price:
        qs = qs.filter(price_per_day__lte=parsed.max_price)

    # Фильтр по доступности в выбранные даты
    if parsed.start_date and parsed.end_date:
        try:
            from rentals.models import Rental
            start = datetime.strptime(parsed.start_date, '%Y-%m-%d').date()
            end = datetime.strptime(parsed.end_date, '%Y-%m-%d').date()
            busy_ids = Rental.objects.filter(
                status__in=['confirmed', 'active'],
                start_date__date__lt=end,
                end_date__date__gt=start,
            ).values_list('inventory_id', flat=True)
            qs = qs.exclude(inventory_id__in=busy_ids)
        except Exception as exc:
            logger.warning('Ошибка фильтрации по датам: %s', exc)

    return qs[:MAX_RESULTS]

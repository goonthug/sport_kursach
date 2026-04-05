"""
Утилиты для отзывов (без привязки к HTTP views).
"""

import logging
from django.db.models import Avg

from reviews.models import Review

logger = logging.getLogger('reviews')


def update_inventory_rating(inventory):
    """Пересчёт среднего рейтинга и числа отзывов по инвентарю."""
    try:
        avg_rating = Review.objects.filter(
            reviewed_id=inventory.inventory_id,
            target_type='inventory',
            status='published',
        ).aggregate(avg=Avg('rating'))['avg']

        if avg_rating is not None:
            inventory.avg_rating = round(float(avg_rating), 2)
        else:
            inventory.avg_rating = None

        inventory.reviews_count = Review.objects.filter(
            reviewed_id=inventory.inventory_id,
            target_type='inventory',
            status='published',
        ).count()

        inventory.save(update_fields=['avg_rating', 'reviews_count'])
    except Exception as e:
        logger.error('Ошибка при обновлении рейтинга инвентаря: %s', e)
